UV ?= uv
DBT_PROJECT_DIR ?= dbt
DBT_PROFILES_DIR ?= dbt
TUNED_CONFIG ?= configs/tuned/all_models.yaml

.PHONY: install download-data build-raw dbt-build dbt-test evidence-install evidence-sources evidence-dev baseline-metrics baseline-submission validate-submission submit-kaggle tune-catboost tune-xgboost tune-lightgbm train-model predict-model compare-models ensemble explain test lint

install:
	$(UV) sync --extra dev

download-data:
	$(UV) run datathon download-data

build-raw:
	$(UV) run datathon build-raw --strict

dbt-build:
	$(UV) run dbt build --project-dir $(DBT_PROJECT_DIR) --profiles-dir $(DBT_PROFILES_DIR)

dbt-test:
	$(UV) run dbt test --project-dir $(DBT_PROJECT_DIR) --profiles-dir $(DBT_PROFILES_DIR)

evidence-install:
	npm --prefix reports/evidence install

evidence-sources:
	npm --prefix reports/evidence run sources

evidence-dev:
	npm --prefix reports/evidence run dev

baseline-metrics:
	$(UV) run datathon baseline --mode evaluate

baseline-submission:
	$(UV) run datathon baseline --mode submit --output-path data/submissions/submission.csv

validate-submission:
	$(UV) run datathon submit-kaggle --dry-run --file data/submissions/best_submission.csv

submit-kaggle:
	$(UV) run datathon submit-kaggle --message "submission"

tune-catboost:
	$(UV) run datathon tune --model-type catboost --n-trials 30 --patience 5

tune-xgboost:
	$(UV) run datathon tune --model-type xgboost --n-trials 30 --patience 5

tune-lightgbm:
	$(UV) run datathon tune --model-type lightgbm --n-trials 30 --patience 5

train-model:
	$(UV) run datathon train --mode train-final --model-type lightgbm --config $(TUNED_CONFIG)

predict-model:
	$(UV) run datathon predict --model-type lightgbm

compare-models:
	$(UV) run datathon compare-models --config $(TUNED_CONFIG)

ensemble:
	$(UV) run datathon ensemble --model-types lightgbm,xgboost,catboost

explain:
	$(UV) run datathon explain --model-type lightgbm

test:
	$(UV) run pytest -q

lint:
	$(UV) run ruff check .
