from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from datathon.modeling.explainer import _save_shap_plots, explain_forecaster


def _make_mock_shap_module():
    """Build a mock ``shap`` module that can replace the real one in sys.modules."""
    mod = MagicMock()
    mock_explainer = MagicMock()
    mod.TreeExplainer = MagicMock(return_value=mock_explainer)
    mod.summary_plot = MagicMock()
    return mod, mock_explainer


def _make_dummy_forecaster() -> MagicMock:
    forecaster = MagicMock()
    forecaster.model_rev = MagicMock()
    forecaster.model_cogs = MagicMock()
    return forecaster


def _make_history(n: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2023-01-01", periods=n)
    cols = {
        "sales_date": dates,
        "revenue": rng.random(n) * 1e6,
        "cogs": rng.random(n) * 8e5,
        "feature_a": rng.random(n),
        "feature_b": rng.random(n),
    }
    return pd.DataFrame(cols)


class TestExplainForecaster:
    def test_returns_revenue_and_cogs_keys(self) -> None:
        mock_shap, mock_explainer = _make_mock_shap_module()
        mock_explainer.shap_values.return_value = np.random.randn(10, 2)

        with patch.dict(sys.modules, {"shap": mock_shap}):
            forecaster = _make_dummy_forecaster()
            history = _make_history(20)
            result = explain_forecaster(forecaster, history, output_dir=None, sample_size=10)

        assert "revenue" in result
        assert "cogs" in result
        rev_df = result["revenue"]
        assert list(rev_df.columns) == ["feature", "mean_abs_shap"]
        assert len(rev_df) == 2  # feature_a, feature_b

    def test_raises_when_missing_model_attributes(self) -> None:
        forecaster = MagicMock()
        del forecaster.model_rev
        history = _make_history(10)

        with pytest.raises(RuntimeError, match="model_rev and model_cogs"):
            explain_forecaster(forecaster, history)

    def test_sampling_uses_sample_size(self) -> None:
        mock_shap, mock_explainer = _make_mock_shap_module()
        mock_explainer.shap_values.return_value = np.random.randn(5, 2)

        with patch.dict(sys.modules, {"shap": mock_shap}):
            forecaster = _make_dummy_forecaster()
            history = _make_history(100)
            explain_forecaster(forecaster, history, output_dir=None, sample_size=5)

        # TreeExplainer should be called with sampled background
        call_args = mock_explainer.shap_values.call_args_list[0]
        X_bg = call_args[0][0]
        assert len(X_bg) == 5

    def test_saves_plots_when_output_dir_provided(self, tmp_path) -> None:
        mock_shap, mock_explainer = _make_mock_shap_module()
        mock_explainer.shap_values.return_value = np.random.randn(5, 2)

        forecaster = _make_dummy_forecaster()
        history = _make_history(20)
        out_dir = tmp_path / "shap"

        with patch.dict(sys.modules, {"shap": mock_shap}):
            explain_forecaster(forecaster, history, output_dir=out_dir, sample_size=5)

        assert (out_dir / "revenue_summary.png").exists()
        assert (out_dir / "revenue_bar.png").exists()
        assert (out_dir / "cogs_summary.png").exists()
        assert (out_dir / "cogs_bar.png").exists()


def test_save_shap_plots_creates_files(tmp_path) -> None:
    """Test the helper directly with a minimal mock."""
    shap_values = np.random.randn(10, 3)
    X_bg = pd.DataFrame({"a": [1.0] * 10, "b": [2.0] * 10, "c": [3.0] * 10})
    out_dir = tmp_path / "plots"

    mock_shap, _ = _make_mock_shap_module()
    with patch.dict(sys.modules, {"shap": mock_shap}):
        _save_shap_plots(shap_values, X_bg, "revenue", out_dir, max_display=3)

    assert (out_dir / "revenue_summary.png").exists()
    assert (out_dir / "revenue_bar.png").exists()
