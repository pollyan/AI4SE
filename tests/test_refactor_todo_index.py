from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFACTOR_DIR = ROOT / "docs" / "todos" / "refactor"
README = REFACTOR_DIR / "README.md"


def active_refactor_todos() -> list[str]:
    return sorted(
        path.name
        for path in REFACTOR_DIR.glob("*.md")
        if path.name != "README.md"
        and "> 状态: 活动候选" in path.read_text(encoding="utf-8")
    )


def test_refactor_readme_current_entries_match_active_candidates() -> None:
    readme = README.read_text(encoding="utf-8")
    active_files = active_refactor_todos()

    if not active_files:
        assert "暂无。" in readme
        return

    assert "当前入口\n\n暂无。" not in readme
    for file_name in active_files:
        assert file_name in readme
