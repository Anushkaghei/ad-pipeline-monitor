.PHONY: help setup up down restart logs seed ingest monitor dbt-run dbt-test api test lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Docker ───────────────────────────────────────────────────
up: ## Start all services
	docker-compose up -d --build

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose down && docker-compose up -d --build

logs: ## Tail all container logs
	docker-compose logs -f

logs-app: ## Tail app container logs
	docker-compose logs -f app

logs-api: ## Tail API container logs
	docker-compose logs -f api

# ── Database ─────────────────────────────────────────────────
setup: ## Initialize database schema
	docker-compose exec app python -m scripts.setup_db

seed: ## Load seed / sample data
	docker-compose exec app python -m scripts.seed_data

# ── Pipeline ─────────────────────────────────────────────────
ingest: ## Run ingestion pipeline
	docker-compose exec app python -m scripts.run_ingestion

monitor: ## Run monitoring checks
	docker-compose exec app python -m scripts.run_monitoring

pipeline: ## Run full pipeline (ingest → dbt → monitor)
	docker-compose exec app python -m scripts.run_pipeline

# ── dbt ──────────────────────────────────────────────────────
dbt-run: ## Run dbt models
	docker-compose exec dbt dbt run --profiles-dir /dbt --project-dir /dbt

dbt-test: ## Run dbt tests
	docker-compose exec dbt dbt test --profiles-dir /dbt --project-dir /dbt

dbt-seed: ## Run dbt seeds
	docker-compose exec dbt dbt seed --profiles-dir /dbt --project-dir /dbt

dbt-debug: ## Debug dbt connection
	docker-compose exec dbt dbt debug --profiles-dir /dbt --project-dir /dbt

# ── API ──────────────────────────────────────────────────────
api: ## Start FastAPI dev server (local, no Docker)
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# ── Testing ──────────────────────────────────────────────────
test: ## Run pytest suite
	python -m pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage
	python -m pytest tests/ -v --tb=short --cov=. --cov-report=html

# ── Linting ──────────────────────────────────────────────────
lint: ## Lint with ruff
	ruff check .

lint-fix: ## Auto-fix lint issues
	ruff check --fix .

# ── Cleanup ──────────────────────────────────────────────────
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist build htmlcov .coverage
