UV ?= uv
DBT_PROJECT_DIR ?= dbt
DBT_PROFILES_DIR ?= dbt

.PHONY: install download-data build-raw dbt-build dbt-test evidence-install evidence-sources evidence-dev evidence-build evidence-deploy evidence-deploy-cf test lint

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

evidence-build:
	cd reports/evidence && npm ci && npm run sources && npm run build

evidence-deploy:
	cd reports/evidence && npx netlify deploy --prod --dir=build

evidence-deploy-cf:
	cd reports/evidence && npx wrangler pages deploy build --project-name=datathon-helicopter --branch=main

test:
	$(UV) run pytest -q

lint:
	$(UV) run ruff check .