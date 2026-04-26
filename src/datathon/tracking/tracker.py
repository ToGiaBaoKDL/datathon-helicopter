"""MLflow tracking wrapper with graceful degradation."""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Any

from datathon.utils.config import load_tracking_config


class _NoOpTracker:
    """Drop-in replacement when MLflow is disabled."""

    enabled: bool = False
    run_id: str | None = None

    def log_param(self, key: str, value: Any) -> None:
        pass

    def log_params(self, params: dict[str, Any]) -> None:
        pass

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        pass

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        pass

    def log_artifact(self, local_path: str | Path) -> None:
        pass

    def log_dict(self, data: dict, artifact_file: str) -> None:
        pass

    def log_model(self, model_path: Path, artifact_path: str = "model") -> None:
        pass

    def set_tag(self, key: str, value: str) -> None:
        pass

    def log_config(self, config: dict[str, Any]) -> None:
        pass

    def log_cv_results(self, results: dict[str, list[dict]], prefix: str = "") -> None:
        pass

    def end_run(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class MlflowTracker:
    """Optional MLflow tracker.

    If ``tracking_uri`` is not configured (null / missing), all methods
    become no-ops so the pipeline still runs without a tracking server.

    """

    def __new__(cls, run_name: str | None = None, **overrides: Any):
        cfg = load_tracking_config()
        uri = (
            overrides.get("tracking_uri")
            or os.getenv("MLFLOW_TRACKING_URI")
            or cfg.get("tracking_uri")
        )
        if uri is None or uri == "null":
            return _NoOpTracker()
        return super().__new__(cls)

    def __init__(self, run_name: str | None = None, **overrides: Any):
        import mlflow

        self._mlflow = mlflow
        cfg = load_tracking_config()

        self.tracking_uri = (
            overrides.get("tracking_uri")
            or os.getenv("MLFLOW_TRACKING_URI")
            or cfg.get("tracking_uri")
        )
        self.artifact_uri = (
            overrides.get("artifact_uri")
            or os.getenv("MLFLOW_ARTIFACT_URI")
            or cfg.get("artifact_uri")
        )
        self.experiment_name = overrides.get("experiment_name") or cfg.get(
            "experiment_name", "datathon_forecasting"
        )
        self.log_models = overrides.get("log_models", cfg.get("log_models", True))
        self.log_artifacts = overrides.get("log_artifacts", cfg.get("log_artifacts", True))

        try:
            mlflow.set_tracking_uri(self.tracking_uri)

            # Ensure parent directory exists for file-based SQLite URIs so that
            # SQLite does not silently create a read-only fallback.
            if self.tracking_uri.startswith("sqlite:///"):
                db_path = Path(self.tracking_uri.replace("sqlite:///", ""))
                db_path.parent.mkdir(parents=True, exist_ok=True)

            if self.artifact_uri:
                os.environ["MLFLOW_ARTIFACT_URI"] = self.artifact_uri
                Path(self.artifact_uri.replace("file:", "")).mkdir(parents=True, exist_ok=True)

            exp = mlflow.get_experiment_by_name(self.experiment_name)
            if exp is None:
                artifact_location = self.artifact_uri or "file:./mlflow/artifacts"
                mlflow.create_experiment(self.experiment_name, artifact_location=artifact_location)
            mlflow.set_experiment(self.experiment_name)

            self.enabled = True
            self._active_run = mlflow.start_run(run_name=run_name)
            self.run_id = self._active_run.info.run_id
        except Exception as exc:
            warnings.warn(
                f"MLflow initialization failed ({exc}); tracking disabled for this run.",
                stacklevel=2,
            )
            self.enabled = False
            self._active_run = None
            self.run_id = None

    # ── context manager ───────────────────────────────
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_run()
        return False

    # ── primitives ────────────────────────────────────
    def log_param(self, key: str, value: Any) -> None:
        if self.enabled:
            self._mlflow.log_param(key, value)

    def log_params(self, params: dict[str, Any]) -> None:
        if self.enabled:
            flat: dict[str, Any] = {}
            for k, v in params.items():
                if isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        flat[f"{k}.{sub_k}"] = sub_v
                else:
                    flat[k] = v
            self._mlflow.log_params(flat)

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        if self.enabled:
            self._mlflow.log_metric(key, float(value), step=step)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        if self.enabled:
            for k, v in metrics.items():
                self._mlflow.log_metric(k, float(v), step=step)

    def log_artifact(self, local_path: str | Path) -> None:
        if self.enabled and self.log_artifacts:
            self._mlflow.log_artifact(str(local_path))

    def log_dict(self, data: dict, artifact_file: str) -> None:
        if self.enabled and self.log_artifacts:
            self._mlflow.log_dict(data, artifact_file)

    def log_model(self, model_path: Path, artifact_path: str = "model") -> None:
        """Log pickled forecaster + meta.json as an artifact folder."""
        if self.enabled and self.log_models:
            self._mlflow.log_artifacts(str(model_path), artifact_path=artifact_path)

    def set_tag(self, key: str, value: str) -> None:
        if self.enabled:
            self._mlflow.set_tag(key, value)

    # ── helpers ───────────────────────────────────────
    def log_config(self, config: dict[str, Any]) -> None:
        """Log modeling config as artifact + flatten params for UI filtering."""
        if not self.enabled:
            return
        self.log_dict(config, "modeling_config.json")
        for k, v in config.items():
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    self.log_param(f"config.{k}.{sub_k}", sub_v)
            else:
                self.log_param(f"config.{k}", v)

    def log_git_info(self) -> None:
        """Log current git commit hash and dirty status if available."""
        if not self.enabled:
            return
        try:
            import subprocess

            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=Path(__file__).resolve().parent,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            dirty = (
                subprocess.check_output(
                    ["git", "status", "--porcelain"],
                    cwd=Path(__file__).resolve().parent,
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                != ""
            )
            self.set_tag("git_commit", commit)
            self.set_tag("git_dirty", "true" if dirty else "false")
        except Exception:
            pass

    def log_cv_results(self, results: dict[str, list[dict]], prefix: str = "") -> None:
        """Log per-fold CV metrics with fold number as step."""
        if not self.enabled:
            return
        for target, folds in results.items():
            for fold_res in folds:
                fold = fold_res["fold"]
                for metric, val in fold_res.items():
                    if metric == "fold":
                        continue
                    key = f"{prefix}{target}_{metric}"
                    self.log_metric(key, float(val), step=fold)

    def end_run(self) -> None:
        if self.enabled and self._active_run is not None:
            self._mlflow.end_run()
            self.enabled = False
            self._active_run = None
