.PHONY: help dev up down logs

# Default target
help:
	@echo "Available targets:"
	@echo "  dev        - Run app locally (without docker)"
	@echo "  up         - Docker compose up --build"
	@echo "  down       - Docker compose down -v"
	@echo "  logs       - Docker compose logs -f api"

# Run development server locally
dev:
	cd backend && python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Docker compose up with build (includes CoexistAI service)
up:
	docker compose up --build

# Docker compose down with volumes
down:
	docker compose down -v

# Follow logs for api service
logs:
	docker compose logs -f api