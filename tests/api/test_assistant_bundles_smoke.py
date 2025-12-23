import os
import json
from pathlib import Path

import pytest


def test_assistant_bundles_files_exist():
    base = Path(__file__).resolve().parents[2]
    bundles = base / "assistant-bundles"
    assert (bundles / "intelligent-requirements-analyst-bundle.txt").exists()
    assert (bundles / "testmaster-song-bundle.txt").exists()


def test_get_assistant_bundle_endpoint(api_client, assert_api_response):
    # 仅验证接口存在与返回结构，不依赖真实AI
    resp = api_client.get("/api/requirements/assistants/alex/bundle")
    data = assert_api_response(resp, 200)
    assert "bundle_content" in data
    assert "assistant_info" in data
    assert "Alex" in json.dumps(data["assistant_info"], ensure_ascii=False)

    resp2 = api_client.get("/api/requirements/assistants/lisa/bundle")
    data2 = assert_api_response(resp2, 200)
    assert "bundle_content" in data2
    assert "assistant_info" in data2
    assert "Lisa" in json.dumps(data2["assistant_info"], ensure_ascii=False)

