#!/bin/bash
# Local Development Environment Setup
# Run this once to configure your local environment

set -e

echo "=== Clinical Trial Data Platform - Local Setup ==="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✓ Python version: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
echo "✓ Virtual environment ready"

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install -r requirements-dev.txt -q
echo "✓ Dependencies installed"

# Install pre-commit hooks
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo "✓ Pre-commit hooks installed"
fi

# Check AWS CLI
if command -v aws &> /dev/null; then
    echo "✓ AWS CLI available"
    
    if aws sts get-caller-identity &> /dev/null; then
        echo "✓ AWS credentials configured"
    else
        echo "⚠ AWS credentials not configured (run 'aws configure')"
    fi
else
    echo "⚠ AWS CLI not installed (optional for local development)"
fi

# Check Terraform
if command -v terraform &> /dev/null; then
    TF_VERSION=$(terraform version | head -n1)
    echo "✓ Terraform: $TF_VERSION"
else
    echo "⚠ Terraform not installed (needed for deployment)"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Generate test data: make generate-data-small"
echo "  3. Run tests: make test"
echo ""
