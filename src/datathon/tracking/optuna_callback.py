"""Optuna callback that logs each trial as a nested MLflow run."""

from __future__ import annotations

from typing import TYPE_CHECKING

import optuna

import mlflow

if TYPE_CHECKING:
    from datathon.tracking.tracker import MlflowTracker


class OptunaMLflowCallback:
    """Log each Optuna trial into a nested MLflow run.

    Assumes the parent MLflow run is already active (e.g. inside a
    ``with MlflowTracker(...)`` block).  Each trial becomes a child run
    so hyperparameters and per-trial metrics are browsable in the UI.

    Usage
    -----
    .. code-block:: python

        tracker = MlflowTracker(run_name="tune_lightgbm")
        callback = OptunaMLflowCallback(tracker)
        study.optimize(objective, n_trials=50, callbacks=[callback, stop_callback])
    """

    def __init__(self, tracker: MlflowTracker):
        self.tracker = tracker

    def __call__(self, study: optuna.Study, trial: optuna.trial.FrozenTrial) -> None:
        if not getattr(self.tracker, "enabled", False):
            return

        # ``nested=True`` creates a child run of the currently-active
        # parent run.  We do *not* pass ``run_id`` here — that would
        # resume the parent instead of creating a child.
        with mlflow.start_run(nested=True):
            mlflow.set_tag("trial_number", str(trial.number))
            mlflow.log_params(trial.params)

            if trial.value is not None:
                mlflow.log_metric("total_mae", float(trial.value))

            mlflow.set_tag("trial_state", trial.state.name)

            # Log per-fold intermediate values if available
            for step, val in enumerate(trial.intermediate_values.values()):
                mlflow.log_metric("cumulative_mae", float(val), step=step)
