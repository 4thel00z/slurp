.PHONY: help install format lint test pre-commit-install pre-commit-run pre-commit-update clean

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies including dev dependencies
	uv sync --all-extras

format:  ## Format code with ruff
	uv run ruff format .
	uv run ruff check --fix .

lint:  ## Run linters (ruff and mypy)
	uv run ruff check .
	uv run mypy .

lint-fix:  ## Run linters with auto-fix
	uv run ruff check --fix .

test:  ## Run tests with pytest
	uv run pytest

coverage:  ## Run tests with coverage
	uv run pytest --cov=slurp --cov-report=html --cov-report=term

pre-commit-install:  ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-run:  ## Run pre-commit on all files
	uv run pre-commit run --all-files

pre-commit-update:  ## Update pre-commit hooks to latest versions
	uv run pre-commit autoupdate

clean:  ## Clean up cache files and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage

dev-setup: install pre-commit-install  ## Complete development environment setup
	@echo "✅ Development environment is ready!"
	@echo "Run 'make help' to see available commands"
