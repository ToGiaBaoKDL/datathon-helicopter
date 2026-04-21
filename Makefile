UV ?= uv
DBT_PROJECT_DIR ?= dbt
DBT_PROFILES_DIR ?= dbt

.PHONY: install download-data build-raw dbt-build dbt-test export-model-data evidence-install evidence-sources evidence-dev baseline-metrics baseline-submission submit-kaggle train-model predict-model compare-models test lint

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

export-model-data:
	$(UV) run datathon export-model-data

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
	$(UV) run datathon submit-kaggle --dry-run --file data/submissions/submission.csv

submit-kaggle:
	$(UV) run datathon submit-kaggle --message "submission"

train-model:
	$(UV) run datathon train --mode train-final --model-type lightgbm

predict-model:
	$(UV) run datathon predict --model-type lightgbm

compare-models:
	$(UV) run datathon compare-models --n-folds 2 --horizon-days 30

test:
	$(UV) run pytest -q

lint:
	$(UV) run ruff check .
