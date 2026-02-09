.PHONY: help install install-dev test lint format clean generate-data deploy-dev deploy-prod teardown

# Default target
help:
	@echo "Clinical Trial Data Platform - Available Commands"
	@echo "=================================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo "  make setup-hooks      Set up pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-cov         Run tests with coverage report"
	@echo "  make lint             Run linting checks"
	@echo "  make format           Format code with black and isort"
	@echo "  make type-check       Run mypy type checking"
	@echo ""
	@echo "Data:"
	@echo "  make generate-data    Generate synthetic clinical trial data"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make tf-init          Initialize Terraform"
	@echo "  make tf-plan-dev      Plan dev infrastructure changes"
	@echo "  make tf-apply-dev     Apply dev infrastructure"
	@echo "  make tf-destroy-dev   Destroy dev infrastructure"
	@echo "  make deploy-dev       Full deploy to dev environment"
	@echo "  make teardown         Tear down all AWS resources (cost saving)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            Remove build artifacts and caches"
	@echo "  make docs             Build documentation"

# ============================================================================
# SETUP
# ============================================================================

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

setup-hooks:
	pre-commit install

# ============================================================================
# DEVELOPMENT
# ============================================================================

test:
	pytest src/ -v

test-unit:
	pytest src/ -v -m "unit"

test-integration:
	pytest src/ -v -m "integration"

test-cov:
	pytest src/ --cov=src --cov-report=html --cov-report=term-missing

lint:
	flake8 src/ data/
	black --check src/ data/
	isort --check-only src/ data/

format:
	black src/ data/
	isort src/ data/

type-check:
	mypy src/

# ============================================================================
# DATA GENERATION
# ============================================================================

generate-data:
	python data/synthetic/generator.py --subjects 1000 --output data/synthetic/output/

generate-data-small:
	python data/synthetic/generator.py --subjects 100 --output data/synthetic/output/

# ============================================================================
# TERRAFORM / INFRASTRUCTURE
# ============================================================================

tf-init:
	cd infrastructure/terraform && terraform init

tf-plan-dev:
	cd infrastructure/terraform && terraform workspace select dev || terraform workspace new dev
	cd infrastructure/terraform && terraform plan -var-file=environments/dev.tfvars

tf-apply-dev:
	cd infrastructure/terraform && terraform workspace select dev
	cd infrastructure/terraform && terraform apply -var-file=environments/dev.tfvars

tf-destroy-dev:
	cd infrastructure/terraform && terraform workspace select dev
	cd infrastructure/terraform && terraform destroy -var-file=environments/dev.tfvars

deploy-dev: tf-init tf-apply-dev
	@echo "Development environment deployed successfully!"

teardown:
	@echo "Tearing down all AWS resources..."
	./scripts/teardown_aws.sh
	@echo "Teardown complete. All resources destroyed."

# ============================================================================
# UTILITIES
# ============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf build/ dist/ 2>/dev/null || true

docs:
	mkdocs build

docs-serve:
	mkdocs serve
