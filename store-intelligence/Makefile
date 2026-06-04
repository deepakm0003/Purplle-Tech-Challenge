# Development Makefile

.PHONY: help install install-dev run dev test test-cov lint format clean docker-up docker-down db-init db-migrate

help:
	@echo "Store Intelligence System - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies"
	@echo "  make install-dev      Install dev dependencies"
	@echo ""
	@echo "Running:"
	@echo "  make run              Run FastAPI server"
	@echo "  make dev              Run with auto-reload"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linting (flake8, mypy)"
	@echo "  make format           Format code (black, isort)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up        Start containers"
	@echo "  make docker-down      Stop containers"
	@echo ""
	@echo "Database:"
	@echo "  make db-init          Initialize database schema"
	@echo "  make db-migrate       Run pending migrations"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove cache and temp files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov black isort flake8 mypy

run:
	uvicorn api.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v

test-cov:
	pytest --cov=. --cov-report=html --cov-report=term-missing -v

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	mypy . --ignore-missing-imports 2>/dev/null || true

format:
	black .
	isort .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov dist build *.egg-info

docker-up:
	docker-compose up -d
	@echo "Services started. API: http://localhost:8000"

docker-down:
	docker-compose down
	@echo "Services stopped"

db-init:
	python -c "import asyncio; from storage import init_db; asyncio.run(init_db())"
	@echo "Database initialized"

db-migrate:
	alembic upgrade head

.DEFAULT_GOAL := help
