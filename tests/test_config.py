from __future__ import annotations

from career_ops.config import (
    get_additions_dir,
    get_apps_file,
    get_job_tracker_file,
    get_output_dir,
    get_pipeline_file,
    get_reports_dir,
    get_states_file,
)


def test_resolvers_are_workspace_only(career_ops_root):
    root = career_ops_root

    assert get_apps_file(root) == root / "workspace" / "applications.md"
    assert get_pipeline_file(root) == root / "workspace" / "pipeline.md"
    assert get_job_tracker_file(root) == root / "workspace" / "job-tracker.csv"
    assert get_output_dir(root) == root / "workspace" / "output"
    assert get_additions_dir(root) == root / "workspace" / "tracker-additions"
    assert get_reports_dir(root) == root / "workspace" / "reports"
    assert get_states_file(root) == root / "config" / "states.yml"


def test_resolvers_ignore_legacy_layouts(career_ops_root):
    root = career_ops_root
    (root / "data" / "applications.md").write_text("legacy", encoding="utf-8")
    (root / "data" / "pipeline.md").write_text("legacy", encoding="utf-8")
    (root / "data" / "job-tracker.csv").write_text("legacy", encoding="utf-8")
    (root / "output").mkdir(exist_ok=True)
    (root / "templates" / "states.yml").write_text("legacy", encoding="utf-8")

    assert get_apps_file(root) == root / "workspace" / "applications.md"
    assert get_pipeline_file(root) == root / "workspace" / "pipeline.md"
    assert get_job_tracker_file(root) == root / "workspace" / "job-tracker.csv"
    assert get_output_dir(root) == root / "workspace" / "output"
    assert get_additions_dir(root) == root / "workspace" / "tracker-additions"
    assert get_reports_dir(root) == root / "workspace" / "reports"
    assert get_states_file(root) == root / "config" / "states.yml"
