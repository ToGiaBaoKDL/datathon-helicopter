from __future__ import annotations

import pandas as pd
import pytest

from datathon.modeling.cv import ExpandingWindowCV


def _make_df(n: int = 100) -> pd.DataFrame:
    return pd.DataFrame({"sales_date": pd.date_range("2023-01-01", periods=n)})


def test_cv_yields_correct_number_of_folds() -> None:
    cv = ExpandingWindowCV(n_folds=3, horizon_days=10)
    splits = list(cv.split(_make_df(100)))
    assert len(splits) == 3


def test_cv_train_increases_each_fold() -> None:
    cv = ExpandingWindowCV(n_folds=3, horizon_days=10)
    splits = list(cv.split(_make_df(100)))
    train_lens = [len(train_idx) for _, train_idx, _ in splits]
    assert train_lens == [70, 80, 90]


def test_cv_val_fixed_length() -> None:
    cv = ExpandingWindowCV(n_folds=3, horizon_days=10)
    splits = list(cv.split(_make_df(100)))
    for _, _, val_idx in splits:
        assert len(val_idx) == 10


def test_cv_train_val_no_overlap() -> None:
    cv = ExpandingWindowCV(n_folds=3, horizon_days=10)
    for _, train_idx, val_idx in cv.split(_make_df(100)):
        assert max(train_idx) < min(val_idx)


def test_cv_single_fold() -> None:
    cv = ExpandingWindowCV(n_folds=1, horizon_days=10)
    splits = list(cv.split(_make_df(100)))
    assert len(splits) == 1
    assert len(splits[0][1]) == 90  # train
    assert len(splits[0][2]) == 10  # val


def test_cv_not_enough_rows_raises() -> None:
    cv = ExpandingWindowCV(n_folds=3, horizon_days=50)
    with pytest.raises(ValueError, match="Not enough rows"):
        list(cv.split(_make_df(100)))


def test_cv_horizon_larger_than_data() -> None:
    cv = ExpandingWindowCV(n_folds=1, horizon_days=200)
    with pytest.raises(ValueError, match="Not enough rows"):
        list(cv.split(_make_df(100)))


def test_cv_val_clipped_at_end() -> None:
    """When horizon would exceed data length, val is clipped."""
    cv = ExpandingWindowCV(n_folds=1, horizon_days=15)
    splits = list(cv.split(_make_df(100)))
    assert len(splits[0][2]) == 15
