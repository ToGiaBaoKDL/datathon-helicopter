"""Validate that the SQL mart and the Python recursive engine stay in sync.

Detects missing columns, unexpected exogenous columns, and drift between
what the model expects and what the database provides.
"""

from __future__ import annotations

from pathlib import Path

from datathon.modeling.recursive import (
    _META_COLUMNS,
    _TARGET_DERIVED,
    CALENDAR_FEATURES,
)
from datathon.utils.data_loaders import load_modeling_data


def validate_mart_vs_recursive(warehouse: Path | None = None) -> dict:
    """Check that every column in the mart is classified by recursive.py.

    Returns
    -------
    dict with keys ``unclassified``, ``missing_calendar``, ``missing_target_derived``,
    ``missing_meta``.
    """
    df = load_modeling_data(warehouse)
    cols = set(df.columns)

    classified = set(CALENDAR_FEATURES) | set(_TARGET_DERIVED) | _META_COLUMNS
    unclassified = cols - classified

    missing_calendar = set(CALENDAR_FEATURES) - cols
    missing_target_derived = set(_TARGET_DERIVED) - cols
    missing_meta = _META_COLUMNS - cols

    return {
        "unclassified": sorted(unclassified),
        "missing_calendar": sorted(missing_calendar),
        "missing_target_derived": sorted(missing_target_derived),
        "missing_meta": sorted(missing_meta),
        "is_valid": not any([unclassified, missing_calendar, missing_target_derived, missing_meta]),
    }
