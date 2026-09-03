"""What the assets need from outside the process."""

from __future__ import annotations

from pathlib import Path

from dagster_dbt import DbtProject

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The manifest is parsed on demand in development and built ahead of time in a
# deployment, so the asset graph is available without a database to talk to.
dbt_project = DbtProject(
    project_dir=PROJECT_ROOT / "warehouse",
    profiles_dir=PROJECT_ROOT / "warehouse",
)
dbt_project.prepare_if_dev()
