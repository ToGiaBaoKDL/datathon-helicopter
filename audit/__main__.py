"""Entry-point for the audit package.

Usage::

    uv run python -m audit
"""

from __future__ import annotations

from audit.data_quality import (
    check_date_gaps,
    check_mart_schema,
    check_nulls,
    check_row_counts,
)
from audit.feature_analysis import (
    autocorrelations,
    feature_correlations,
    quick_feature_importance,
    target_stats,
)
from audit.mart_validation import validate_mart_vs_recursive
from audit.report import generate_report


def main() -> None:
    schema = check_mart_schema()
    nulls = check_nulls()
    row_counts = check_row_counts()
    date_gaps = check_date_gaps()
    targets = target_stats()
    correlations = feature_correlations()
    importance = quick_feature_importance()
    autocorrs = autocorrelations()
    validation = validate_mart_vs_recursive()

    generate_report(
        schema=schema,
        nulls=nulls,
        row_counts=row_counts,
        date_gaps=date_gaps,
        targets=targets,
        correlations=correlations,
        importance=importance,
        autocorrs=autocorrs,
        validation=validation,
    )


if __name__ == "__main__":
    main()
