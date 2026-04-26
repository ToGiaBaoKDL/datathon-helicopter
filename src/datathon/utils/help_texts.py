"""Centralised help text strings for CLI commands."""

from __future__ import annotations

from datathon.modeling.forecasters import list_forecasters

CV_TYPE_HELP = (
    "[dim]--cv-type[/dim]          'sliding' (default) or 'expanding'.\n"
    "  sliding   — fixed train window (~3 yr); preferred for this dataset because\n"
    "              of structural break around 2019 (days_since_2019 feature).\n"
    "  expanding — train set grows each fold; use only when regime is stable.\n"
    "[dim]--train-window-days[/dim]  Training window for 'sliding' CV (default 1096 ≈ 3 yr).\n"
    "[dim]--purge-days[/dim]       Purge gap between train/val (default 7). "
    "Reduces leakage through autocorrelated lag/rolling features."
)

MODELS_LINE = "[dim]Available:[/dim] " + ", ".join(list_forecasters())


def train_help() -> str:
    return (
        "[dim]Usage:[/dim] datathon train --mode <evaluate|train-final> "
        "[--model-type <type>] [--warehouse <path>] [--model-dir <path>] "
        "[--n-folds <int>] [--horizon-days <int>] [--cv-type <type>] "
        "[--train-window-days <int>] [--purge-days <int>] [--config <path>]\n"
        + MODELS_LINE
        + "\n[dim]evaluate[/dim]   Run cross-validation and print metrics.\n"
        "[dim]train-final[/dim] Train on full history and save model artifacts.\n"
        + CV_TYPE_HELP
        + "\n[dim]--config[/dim]   Optional modeling config path "
        "(defaults to configs/modeling.yaml)."
    )


def compare_help() -> str:
    return (
        "[dim]Usage:[/dim] datathon compare-models [--warehouse <path>] "
        "[--n-folds <int>] [--horizon-days <int>] [--cv-type <type>] "
        "[--train-window-days <int>] [--purge-days <int>] "
        "[--model-dir <path>] [--output-path <path>] [--config <path>] [--force]\n"
        "Runs CV for all registered models, evaluates a weighted ensemble "
        "(inverse MAE), picks the winner, trains finals, and generates a submission.\n"
        + CV_TYPE_HELP
        + "\n[dim]--config[/dim]   Optional config (defaults to configs/modeling.yaml).\n"
        "[dim]--force[/dim]    Retrain even if artifacts already exist."
    )


def tune_help() -> str:
    return (
        "[dim]Usage:[/dim] datathon tune [--model-type <type>] [--n-trials <int>] "
        "[--timeout <sec>] [--n-folds <int>] [--horizon-days <int>] "
        "[--cv-type <type>] [--train-window-days <int>] [--purge-days <int>] "
        "[--output-path <path>] [--storage <url>] [--seed <int>] [--config <path>]\n"
        "Run Optuna hyperparameter search. Best params written as a delta config "
        "— pass via --config to train/predict/compare.\n"
        + CV_TYPE_HELP
        + "\n[dim]--storage[/dim]   Use sqlite:///path/to.db to resume interrupted studies."
    )


def predict_help() -> str:
    return (
        "[dim]Usage:[/dim] datathon predict [--model-type <type>] "
        "[--warehouse <path>] [--model-dir <path>] [--output-path <path>]\n"
        "Load a trained model and generate a submission CSV.\n" + MODELS_LINE
    )


def ensemble_help() -> str:
    return (
        "[dim]Usage:[/dim] datathon ensemble [--model-types <t1,t2,...>] "
        "[--weights <w1,w2,...>] [--warehouse <path>] [--model-dir <path>] "
        "[--output-path <path>]\n"
        "Load multiple trained models, average predictions (optionally weighted), "
        "and generate a submission.\n"
        "[dim]Default models:[/dim] lightgbm,xgboost,catboost | [dim]Default weights:[/dim] equal"
    )


def explain_help() -> str:
    return (
        "[dim]Usage:[/dim] datathon explain [--model-type <type>] [--warehouse <path>] "
        "[--model-dir <path>] [--output-dir <path>] [--sample-size <int>] "
        "[--max-display <int>]\n"
        "Generate SHAP summary and bar plots for a trained forecaster. "
        "PNG files saved under [dim]<output-dir>/[/dim]."
    )


def feature_importance_help() -> str:
    return (
        "[dim]Usage:[/dim] datathon feature-importance "
        "[--method <split|permutation|shap|all>] [--top-n <n>] "
        "[--model-type <type>] [--warehouse <path>] [--config <path>]\n"
        "Analyse feature importance:\n"
        "  [dim]split[/dim]        LGBM split-based importance (gain) — fast, default.\n"
        "  [dim]permutation[/dim]  MAE increase when feature is randomly shuffled.\n"
        "  [dim]shap[/dim]         SHAP mean |value| — requires a fitted model.\n"
        "  [dim]all[/dim]          Run all three methods.\n" + MODELS_LINE
    )


def baseline_help() -> str:
    return (
        "[dim]Usage:[/dim] datathon baseline --mode <evaluate|submit> "
        "[--warehouse <path>] [--seasonal-period <int>] [--output-path <path>]\n"
        "[dim]Note:[/dim] --output-path is only valid with --mode submit."
    )
