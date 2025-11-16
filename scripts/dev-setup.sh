#!/bin/bash
set -e

echo "Setting up development environment..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3.11+ is required"; exit 1; }
command -v ruby >/dev/null 2>&1 || { echo "Ruby 3.2+ is required"; exit 1; }

# Copy environment template
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env file - please update with your credentials"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
cd app/ai_service
uv sync --all-extras
cd ../..

# Install Rails dependencies
echo "Installing Rails dependencies..."
cd app/rails_api
bundle install
cd ../..

# Setup pre-commit hooks
echo "Setting up pre-commit hooks..."
pre-commit install

# Start services
echo "Starting Docker services..."
docker-compose up -d postgres redis

# Wait for databases
echo "Waiting for databases..."
sleep 5

# Setup databases
echo "Setting up databases..."
cd app/rails_api
bundle exec rails db:create db:migrate
cd ../..

echo "Setup complete! Run 'docker-compose up' to start all services."
