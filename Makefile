.PHONY: help setup dev up down logs clean

# Default target
help:
	@echo "Available targets:"
	@echo "  setup      - Initial setup: clone CoexistAI and configure environment"
	@echo "  dev        - Run app locally (without docker)"
	@echo "  up         - Docker compose up --build (runs setup first)"
	@echo "  down       - Docker compose down -v"
	@echo "  logs       - Docker compose logs -f api"
	@echo "  clean      - Clean up Docker containers and volumes"
	@echo "  test       - Run API tests"

# Initial setup - clone CoexistAI and configure
setup:
	@echo "🚀 Running initial setup..."
	@chmod +x setup.sh
	@./setup.sh

# Run development server locally
dev:
	cd backend && python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Docker compose up with build (includes CoexistAI service)
# Automatically runs setup first
up: setup
	docker compose up --build

# Docker compose down with volumes
down:
	docker compose down -v

# Follow logs for api service
logs:
	docker compose logs -f api

# Clean up everything
clean:
	docker compose down -v
	docker system prune -f
	@echo "🧹 Cleaned up Docker containers and volumes"

# Run API tests
test:
	@if [ -f "test_api.py" ]; then \
		python test_api.py; \
	else \
		echo "❌ test_api.py not found"; \
	fi

# Quick health check
health:
	@echo "🏥 Checking service health..."
	@curl -s http://localhost:8000/health || echo "❌ Main API not responding"
	@curl -s http://localhost:8001/health || echo "❌ CoexistAI not responding"
	@curl -s http://localhost:8080/health || echo "❌ Runner not responding"