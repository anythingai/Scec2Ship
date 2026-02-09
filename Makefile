VENV_PYTHON ?= .venv/bin/python
VENV_UVICORN ?= .venv/bin/uvicorn
NPM ?= npm

.PHONY: run run-backend run-frontend run-all test clean-runtime help stop

help:
	@echo "Available targets:"
	@echo "  make run          - Start both backend and frontend (recommended)"
	@echo "  make run-backend  - Start only the backend API server"
	@echo "  make run-frontend - Start only the frontend dev server"
	@echo "  make run-all      - Start both services in background"
	@echo "  make stop         - Stop all running services"
	@echo "  make test         - Run backend tests"
	@echo "  make clean-runtime - Clean runtime data (runs/workspaces)"

run: run-all
	@echo ""
	@echo "✅ Both services starting..."
	@echo "   Backend:  http://127.0.0.1:8000"
	@echo "   Frontend: http://localhost:3000"
	@echo ""
	@echo "Press Ctrl+C to stop both services"
	@echo ""
	@trap 'make stop' INT TERM; \
	$(VENV_UVICORN) apps.api.main:app --reload --host 127.0.0.1 --port 8000 & \
	BACKEND_PID=$$!; \
	cd apps/web && $(NPM) run dev & \
	FRONTEND_PID=$$!; \
	wait $$BACKEND_PID $$FRONTEND_PID

run-backend:
	@echo "Starting backend API server..."
	@echo "Backend will be available at http://127.0.0.1:8000"
	@echo "API docs available at http://127.0.0.1:8000/docs"
	@echo ""
	$(VENV_UVICORN) apps.api.main:app --reload --host 127.0.0.1 --port 8000

run-frontend:
	@echo "Starting frontend dev server..."
	@echo "Frontend will be available at http://localhost:3000"
	@echo ""
	cd apps/web && $(NPM) run dev

run-all:
	@echo "Starting both backend and frontend..."
	@echo "Backend:  http://127.0.0.1:8000"
	@echo "Frontend: http://localhost:3000"
	@echo ""
	@echo "Starting backend..."
	@$(VENV_UVICORN) apps.api.main:app --reload --host 127.0.0.1 --port 8000 > /tmp/growpad_backend.log 2>&1 & \
	echo $$! > /tmp/growpad_backend.pid && \
	echo "✅ Backend started (PID: $$(cat /tmp/growpad_backend.pid))"
	@sleep 2
	@echo "Starting frontend..."
	@cd apps/web && $(NPM) run dev > /tmp/growpad_frontend.log 2>&1 & \
	echo $$! > /tmp/growpad_frontend.pid && \
	echo "✅ Frontend started (PID: $$(cat /tmp/growpad_frontend.pid))"
	@echo ""
	@echo "✅ Both services are running!"
	@echo "   View logs: tail -f /tmp/growpad_backend.log /tmp/growpad_frontend.log"
	@echo "   Stop: make stop"

stop:
	@echo "Stopping services..."
	@-if [ -f /tmp/growpad_backend.pid ]; then \
		kill $$(cat /tmp/growpad_backend.pid) 2>/dev/null && echo "✅ Backend stopped" || echo "⚠️ Backend process not found"; \
		rm -f /tmp/growpad_backend.pid; \
	fi
	@-if [ -f /tmp/growpad_frontend.pid ]; then \
		kill $$(cat /tmp/growpad_frontend.pid) 2>/dev/null && echo "✅ Frontend stopped" || echo "⚠️ Frontend process not found"; \
		rm -f /tmp/growpad_frontend.pid; \
	fi
	@-pkill -f "uvicorn apps.api.main" 2>/dev/null && echo "✅ Killed remaining uvicorn processes" || true
	@-pkill -f "next dev" 2>/dev/null && echo "✅ Killed remaining Next.js processes" || true
	@echo "✅ All services stopped"

test:
	@echo "Running backend tests..."
	$(VENV_PYTHON) -m pytest -c apps/api/pytest.ini apps/api/tests

clean-runtime:
	@echo "Cleaning runtime data..."
	rm -rf data/runs/* data/workspaces/* || true
	mkdir -p data/runs data/workspaces
	touch data/runs/.gitkeep data/workspaces/.gitkeep
	@echo "✅ Runtime data cleaned"
