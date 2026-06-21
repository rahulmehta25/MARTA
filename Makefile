# MARTA Platform - Makefile
# Development, testing, and deployment automation

.PHONY: help dev install install-dev test test-unit test-integration test-e2e \
        coverage lint format typecheck security build docker-build docker-up \
        docker-down docker-logs clean deploy-staging deploy-prod frontend-install \
        frontend-test frontend-build docs db-migrate db-reset

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
PYTEST := pytest
DOCKER_COMPOSE := docker compose
NPM := npm

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m

# ============================================================================
# Help
# ============================================================================

help: ## Show this help message
	@echo "$(CYAN)MARTA Platform - Development Commands$(NC)"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ============================================================================
# Development Environment
# ============================================================================

dev: install-dev ## Set up development environment
	@echo "$(GREEN)Development environment ready!$(NC)"

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

install-dev: install ## Install development dependencies
	$(PIP) install -r requirements-dev.txt
	pre-commit install
	@echo "$(GREEN)Development dependencies installed$(NC)"

venv: ## Create virtual environment
	$(PYTHON) -m venv venv
	@echo "$(YELLOW)Activate with: source venv/bin/activate$(NC)"

# ============================================================================
# Testing
# ============================================================================

test: test-unit test-integration ## Run all tests
	@echo "$(GREEN)All tests completed$(NC)"

test-unit: ## Run unit tests
	@echo "$(CYAN)Running unit tests...$(NC)"
	$(PYTEST) tests/unit/ -v --tb=short -x

test-integration: ## Run integration tests
	@echo "$(CYAN)Running integration tests...$(NC)"
	$(PYTEST) tests/integration/ -v --tb=short

test-e2e: ## Run end-to-end tests
	@echo "$(CYAN)Running e2e tests...$(NC)"
	$(PYTEST) tests/e2e/ -v --tb=short

test-performance: ## Run performance tests
	@echo "$(CYAN)Running performance tests...$(NC)"
	$(PYTEST) tests/performance/ -v --tb=short

test-fast: ## Run tests in parallel (fast mode)
	@echo "$(CYAN)Running tests in parallel...$(NC)"
	$(PYTEST) tests/ -v --tb=short -n auto -x

coverage: ## Run tests with coverage report
	@echo "$(CYAN)Running tests with coverage...$(NC)"
	$(PYTEST) tests/ \
		--cov=src \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=50 \
		-v
	@echo "$(GREEN)Coverage report: htmlcov/index.html$(NC)"

coverage-report: ## Open coverage report in browser
	open htmlcov/index.html || xdg-open htmlcov/index.html

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run all linters
	@echo "$(CYAN)Running linters...$(NC)"
	ruff check src/ tests/ --fix
	@echo "$(GREEN)Linting completed$(NC)"

format: ## Format code with ruff and black
	@echo "$(CYAN)Formatting code...$(NC)"
	ruff format src/ tests/
	@echo "$(GREEN)Code formatted$(NC)"

typecheck: ## Run type checking with mypy
	@echo "$(CYAN)Running type checks...$(NC)"
	mypy src/ --ignore-missing-imports --no-strict-optional
	@echo "$(GREEN)Type checking completed$(NC)"

security: ## Run security checks
	@echo "$(CYAN)Running security checks...$(NC)"
	bandit -r src/ -ll
	safety check || true
	@echo "$(GREEN)Security checks completed$(NC)"

check: lint typecheck security ## Run all checks (lint, typecheck, security)
	@echo "$(GREEN)All checks passed$(NC)"

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

# ============================================================================
# Docker
# ============================================================================

docker-build: ## Build Docker images
	@echo "$(CYAN)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)Docker images built$(NC)"

docker-up: ## Start Docker containers
	@echo "$(CYAN)Starting containers...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Containers started$(NC)"
	@echo "  API:       http://localhost:8001"
	@echo "  Dashboard: http://localhost:8501"
	@echo "  Grafana:   http://localhost:3000"

docker-down: ## Stop Docker containers
	@echo "$(CYAN)Stopping containers...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)Containers stopped$(NC)"

docker-logs: ## View Docker logs
	$(DOCKER_COMPOSE) logs -f

docker-clean: ## Remove Docker containers, volumes, and images
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	$(DOCKER_COMPOSE) down -v --rmi local
	@echo "$(GREEN)Docker resources cleaned$(NC)"

docker-shell-api: ## Open shell in API container
	$(DOCKER_COMPOSE) exec marta_api /bin/bash

docker-shell-db: ## Open PostgreSQL shell
	$(DOCKER_COMPOSE) exec postgres psql -U marta_user -d marta_db

# ============================================================================
# Frontend
# ============================================================================

frontend-install: ## Install frontend dependencies
	@echo "$(CYAN)Installing frontend dependencies...$(NC)"
	cd frontend && $(NPM) install
	@echo "$(GREEN)Frontend dependencies installed$(NC)"

frontend-dev: ## Start frontend development server
	@echo "$(CYAN)Starting frontend dev server...$(NC)"
	cd frontend && $(NPM) run dev

frontend-build: ## Build frontend for production
	@echo "$(CYAN)Building frontend...$(NC)"
	cd frontend && $(NPM) run build
	@echo "$(GREEN)Frontend built$(NC)"

frontend-test: ## Run frontend tests
	@echo "$(CYAN)Running frontend tests...$(NC)"
	cd frontend && $(NPM) run test

frontend-lint: ## Lint frontend code
	@echo "$(CYAN)Linting frontend...$(NC)"
	cd frontend && $(NPM) run lint

# ============================================================================
# Database
# ============================================================================

db-migrate: ## Run database migrations
	@echo "$(CYAN)Running migrations...$(NC)"
	alembic upgrade head
	@echo "$(GREEN)Migrations completed$(NC)"

db-migrate-create: ## Create new migration
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-reset: ## Reset database (WARNING: destroys data)
	@echo "$(RED)WARNING: This will destroy all data!$(NC)"
	@read -p "Are you sure? [y/N] " confirm; \
	if [ "$$confirm" = "y" ]; then \
		alembic downgrade base && alembic upgrade head; \
	fi

db-seed: ## Seed database with sample data
	@echo "$(CYAN)Seeding database...$(NC)"
	$(PYTHON) scripts/seed_database.py
	@echo "$(GREEN)Database seeded$(NC)"

# ============================================================================
# Build & Deploy
# ============================================================================

build: docker-build frontend-build ## Build all components
	@echo "$(GREEN)All components built$(NC)"

deploy-staging: build ## Deploy to staging environment
	@echo "$(CYAN)Deploying to staging...$(NC)"
	@echo "$(YELLOW)Configure staging deployment in this target$(NC)"

deploy-prod: ## Deploy to production (requires confirmation)
	@echo "$(RED)Production deployment$(NC)"
	@read -p "Are you sure you want to deploy to production? [y/N] " confirm; \
	if [ "$$confirm" = "y" ]; then \
		echo "$(CYAN)Deploying to production...$(NC)"; \
		echo "$(YELLOW)Configure production deployment in this target$(NC)"; \
	fi

# ============================================================================
# Documentation
# ============================================================================

docs: ## Build documentation
	@echo "$(CYAN)Building documentation...$(NC)"
	mkdocs build
	@echo "$(GREEN)Documentation built$(NC)"

docs-serve: ## Serve documentation locally
	mkdocs serve

# ============================================================================
# Utilities
# ============================================================================

clean: ## Clean build artifacts
	@echo "$(CYAN)Cleaning build artifacts...$(NC)"
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov coverage.xml .coverage
	rm -rf dist build *.egg-info
	rm -rf frontend/dist frontend/node_modules/.vite
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Clean complete$(NC)"

logs: ## View application logs
	tail -f logs/*.log

run-api: ## Run API server locally
	$(PYTHON) run_api.py

run-dashboard: ## Run Streamlit dashboard locally
	streamlit run src/visualization/demo_dashboard.py

run-ingestion: ## Run data ingestion
	$(PYTHON) run_ingestion.py

# ============================================================================
# CI/CD Helpers
# ============================================================================

ci-test: ## Run CI test suite
	$(PYTEST) tests/ \
		--cov=src \
		--cov-report=xml \
		--cov-fail-under=50 \
		--junitxml=pytest-results.xml \
		-v

ci-lint: ## Run CI linting
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports

ci-security: ## Run CI security checks
	bandit -r src/ -f json -o bandit-report.json || true
	safety check --json > safety-report.json || true
