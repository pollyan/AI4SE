from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REFACTOR_TODO_DIR = REPO_ROOT / "docs" / "todos" / "refactor"
README_PATH = REFACTOR_TODO_DIR / "README.md"


def test_refactor_readme_lists_all_active_candidates() -> None:
    active_files = sorted(
        path.name
        for path in REFACTOR_TODO_DIR.glob("*.md")
        if path.name != "README.md"
        and "> 状态: 活动候选" in path.read_text(encoding="utf-8")
    )
    readme = README_PATH.read_text(encoding="utf-8")

    if not active_files:
        assert "当前入口\n\n暂无。" in readme
        return

    assert "当前入口\n\n暂无。" not in readme
    for filename in active_files:
        assert filename in readme
