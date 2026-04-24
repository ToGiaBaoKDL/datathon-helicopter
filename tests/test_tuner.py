from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import optuna
import pandas as pd
import pytest

from datathon.modeling.tuner import (
    _inject_fixed_params,
    _make_stop_callback,
    _suggest_catboost,
    _suggest_lightgbm,
    _suggest_xgboost,
)


def test_inject_fixed_params_adds_missing_keys() -> None:
    tuned = {"learning_rate": 0.05}
    base = {"models": {"lightgbm": {"n_estimators": 500, "objective": "regression"}}}
    result = _inject_fixed_params(tuned, base, "lightgbm")
    assert result["learning_rate"] == 0.05
    assert result["n_estimators"] == 500
    assert result["objective"] == "regression"


def test_inject_fixed_params_does_not_override_tuned() -> None:
    tuned = {"learning_rate": 0.05, "n_estimators": 100}
    base = {"models": {"lightgbm": {"n_estimators": 500}}}
    result = _inject_fixed_params(tuned, base, "lightgbm")
    assert result["n_estimators"] == 100  # tuned wins


def test_inject_fixed_params_missing_model_raises() -> None:
    tuned = {"learning_rate": 0.05}
    base = {"models": {}}
    result = _inject_fixed_params(tuned, base, "lightgbm")
    assert result == tuned  # nothing to inject


class TestSuggestFunctions:
    """Test that each _suggest_* function returns a dict with expected keys."""

    def _make_trial(self, fixed: dict) -> optuna.trial.FixedTrial:
        return optuna.trial.FixedTrial(fixed)

    def test_suggest_lightgbm_keys(self) -> None:
        trial = self._make_trial(
            {
                "learning_rate": 0.1,
                "num_leaves": 31,
                "max_depth": 6,
                "min_child_samples": 20,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_alpha": 1e-3,
                "reg_lambda": 1.0,
            }
        )
        cfg = _suggest_lightgbm(trial)
        expected_keys = {
            "learning_rate",
            "num_leaves",
            "max_depth",
            "min_child_samples",
            "subsample",
            "colsample_bytree",
            "reg_alpha",
            "reg_lambda",
        }
        assert set(cfg.keys()) == expected_keys

    def test_suggest_xgboost_keys(self) -> None:
        trial = self._make_trial(
            {
                "learning_rate": 0.1,
                "max_depth": 6,
                "min_child_weight": 3,
                "gamma": 1e-3,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_alpha": 1e-3,
                "reg_lambda": 1.0,
            }
        )
        cfg = _suggest_xgboost(trial)
        expected_keys = {
            "learning_rate",
            "max_depth",
            "min_child_weight",
            "gamma",
            "subsample",
            "colsample_bytree",
            "reg_alpha",
            "reg_lambda",
        }
        assert set(cfg.keys()) == expected_keys

    def test_suggest_catboost_keys(self) -> None:
        trial = self._make_trial(
            {
                "learning_rate": 0.1,
                "depth": 6,
                "l2_leaf_reg": 3.0,
                "random_strength": 1.0,
                "bagging_temperature": 0.5,
            }
        )
        cfg = _suggest_catboost(trial)
        expected_keys = {
            "learning_rate",
            "depth",
            "l2_leaf_reg",
            "random_strength",
            "bagging_temperature",
        }
        assert set(cfg.keys()) == expected_keys


class TestStopCallback:
    def test_stops_after_patience_trials_without_improvement(self) -> None:
        callback = _make_stop_callback(patience=2)
        study = optuna.create_study(direction="minimize")
        with patch.object(study, "stop") as mock_stop:
            # Trial 1: best = 10
            study.tell(study.ask(), 10.0)
            callback(study, study.trials[-1])
            mock_stop.assert_not_called()

            # Trial 2: worse (15)
            study.tell(study.ask(), 15.0)
            callback(study, study.trials[-1])
            mock_stop.assert_not_called()  # only 1 trial without improvement

            # Trial 3: worse (20) -> should trigger stop
            study.tell(study.ask(), 20.0)
            callback(study, study.trials[-1])
            mock_stop.assert_called_once()

    def test_stops_after_consecutive_worse_trials(self) -> None:
        callback = _make_stop_callback(patience=2)
        study = optuna.create_study(direction="minimize")
        with patch.object(study, "stop") as mock_stop:
            study.tell(study.ask(), 10.0)
            callback(study, study.trials[-1])

            study.tell(study.ask(), 12.0)  # worse
            callback(study, study.trials[-1])
            mock_stop.assert_not_called()  # only 1 worse trial

            study.tell(study.ask(), 13.0)  # worse again -> 2 consecutive worse
            callback(study, study.trials[-1])
            mock_stop.assert_called_once()

    def test_no_stop_before_patience_threshold(self) -> None:
        callback = _make_stop_callback(patience=5)
        study = optuna.create_study(direction="minimize")
        with patch.object(study, "stop") as mock_stop:
            for i in range(3):
                study.tell(study.ask(), float(i + 1))
                callback(study, study.trials[-1])

            mock_stop.assert_not_called()
