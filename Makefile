.PHONY: help install backend frontend ml train test lint docker up down clean

help:
	@echo "JobPair.aloe - commands:"
	@echo "  make install      Install backend + frontend dependencies"
	@echo "  make backend      Run backend dev server"
	@echo "  make frontend     Run frontend dev server"
	@echo "  make ml           Generate synthetic training data + train ML models"
	@echo "  make train        Train PyTorch model only"
	@echo "  make test         Run all tests"
	@echo "  make lint         Run linters"
	@echo "  make docker       Build docker images"
	@echo "  make up           Start docker-compose stack"
	@echo "  make down         Stop docker-compose stack"
	@echo "  make clean        Remove build artifacts and caches"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

ml:
	cd backend && python -m app.ml.train_pipeline

train:
	cd backend && python -m app.ml.train_pipeline --skip-baseline

test:
	cd backend && pytest -v
	cd frontend && npm test

lint:
	cd backend && ruff check app/ && black --check app/
	cd frontend && npm run lint

docker:
	docker-compose build

up:
	docker-compose up -d
	@echo "Waiting for services..."
	@sleep 8
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8000"

down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/htmlcov backend/coverage.xml
	rm -rf frontend/.next frontend/out
