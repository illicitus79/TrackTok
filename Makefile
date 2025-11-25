.PHONY: help install dev migrate seed test lint format clean docker-up docker-down

help:
	@echo "TrackTok - Multi-tenant Expense Tracker"
	@echo ""
	@echo "Available targets:"
	@echo "  install       Install dependencies"
	@echo "  dev           Run development server"
	@echo "  migrate       Run database migrations"
	@echo "  seed          Seed database with demo data"
	@echo "  test          Run tests with coverage"
	@echo "  lint          Run linters (flake8, mypy)"
	@echo "  format        Format code (black, isort)"
	@echo "  clean         Remove generated files"
	@echo "  docker-up     Start Docker containers"
	@echo "  docker-down   Stop Docker containers"

install:
	pip install -r requirements.txt

dev:
	flask run --host=0.0.0.0 --port=5000 --debug

migrate:
	flask db upgrade

migrate-create:
	@read -p "Enter migration message: " msg; \
	flask db migrate -m "$$msg"

seed:
	python scripts/seed.py

test:
	pytest

test-coverage:
	pytest --cov=app --cov-report=html --cov-report=term

lint:
	flake8 app tests
	black --check app tests
	isort --check-only app tests

format:
	black app tests
	isort app tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec web bash

init-db:
	python scripts/init_db.py

worker:
	celery -A app.tasks.celery_app worker --loglevel=info

beat:
	celery -A app.tasks.celery_app beat --loglevel=info

flower:
	celery -A app.tasks.celery_app flower --port=5555

openapi:
	python scripts/export_openapi.py
