"""The code location Dagster serves."""

from __future__ import annotations

import dagster as dg
from dagster_dbt import DbtCliResource

from pipeline import assets
from pipeline.resources import dbt_project

defs = dg.Definitions(
    assets=dg.load_assets_from_modules([assets]),
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
)
