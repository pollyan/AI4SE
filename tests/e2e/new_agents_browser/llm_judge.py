from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[3]
DOTENV_PATH = ROOT / ".env"
_DOTENV_LOADED = False


@dataclass(frozen=True)
class JudgeResult:
    passed: bool
    score: int
    issues: list[str]


def _load_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True

    if not DOTENV_PATH.exists():
        return

    dotenv_values: dict[str, str] = {}
    for raw_line in DOTENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            dotenv_values[key] = value

    for key, value in dotenv_values.items():
        if key not in os.environ:
            os.environ[key] = value


def is_llm_judge_enabled() -> bool:
    _load_dotenv()
    return os.environ.get("NEW_AGENTS_E2E_LLM_JUDGE") == "1"


def assert_llm_judges_artifact_quality(workflow_name: str, artifact: str) -> None:
    _load_dotenv()
    if not is_llm_judge_enabled():
        pytest.skip("NEW_AGENTS_E2E_LLM_JUDGE is not enabled")

    api_key = os.environ.get("NEW_AGENTS_E2E_JUDGE_API_KEY")
    base_url = os.environ.get("NEW_AGENTS_E2E_JUDGE_BASE_URL")
    model = os.environ.get("NEW_AGENTS_E2E_JUDGE_MODEL")
    missing = [
        name
        for name, value in {
            "NEW_AGENTS_E2E_JUDGE_API_KEY": api_key,
            "NEW_AGENTS_E2E_JUDGE_BASE_URL": base_url,
            "NEW_AGENTS_E2E_JUDGE_MODEL": model,
        }.items()
        if not value
    ]
    if missing:
        pytest.skip("missing LLM judge environment variables: " + ", ".join(missing))

    prompt = f"""
请评审以下 New Agents 浏览器测试最终产物是否满足 {workflow_name} 工作流质量要求。
只返回 JSON，不要返回 Markdown。
JSON 结构必须是：{{"pass": true/false, "score": 0-100, "issues": ["问题1"]}}
评审标准：
1. 覆盖工作流要求的主要章节。
2. 内容不是纯占位符。
3. 对真实用户有用。
4. 内部逻辑连贯。

产物：
{artifact}
""".strip()

    response = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "你是严格的软件测试产物评审员。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    result = JudgeResult(
        passed=bool(parsed["pass"]),
        score=int(parsed["score"]),
        issues=list(parsed.get("issues", [])),
    )
    assert result.passed, (
        f"LLM judge failed with score {result.score}: {result.issues}"
    )
    assert result.score >= 70, (
        f"LLM judge score too low: {result.score}, issues: {result.issues}"
    )
