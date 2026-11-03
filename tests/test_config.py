from __future__ import annotations

from career_ops.config import (
    get_cv_output_dir,
    get_db_path,
    get_output_dir,
    get_reports_dir,
    get_states_file,
    resolve_root,
)


def test_resolvers_use_sqlite_and_workspace_layout(career_ops_root):
    root = career_ops_root

    assert get_db_path(root) == root / "data" / "career_ops.db"
    assert get_output_dir(root) == root / "workspace" / "output"
    assert get_cv_output_dir(root) == root / "output" / "cv"
    assert get_reports_dir(root) == root / "output" / "reports"
    assert get_states_file(root) == root / "config" / "states.yml"
    assert resolve_root(str(root)) == root.resolve()


def test_resolvers_ignore_legacy_layouts(career_ops_root):
    root = career_ops_root
    (root / "output").mkdir(exist_ok=True)
    (root / "templates" / "states.yml").write_text("legacy", encoding="utf-8")

    assert get_db_path(root) == root / "data" / "career_ops.db"
    assert get_output_dir(root) == root / "workspace" / "output"
    assert get_reports_dir(root) == root / "output" / "reports"
    assert get_states_file(root) == root / "config" / "states.yml"
