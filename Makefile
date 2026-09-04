.PHONY: help install dev up stop start restart down status health logs preflight config-check reset-data test security secret-scan architecture-check lint format format-check typecheck check clean

PYTHON ?= python3

# Default target
help:
	@echo "============================================================"
	@echo " Mandate Gateway — Developer Command Interface"
	@echo " Current Stage: Foundation Stage (M00 — S00.6 Quality Gates & CI)"
	@echo "============================================================"
	@echo " Infrastructure & Lifecycle Commands:"
	@echo "   make help               - Display this help message"
	@echo "   make preflight          - Validate local environment & configuration"
	@echo "   make config-check       - Display effective configuration metadata (Redacted)"
	@echo "   make install            - Install local toolchain dependencies (black, flake8, mypy)"
	@echo "   make dev                - Launch local development infrastructure (alias for 'up')"
	@echo "   make up                 - Start local Docker infrastructure containers"
	@echo "   make stop               - Suspend local Docker infrastructure containers"
	@echo "   make start              - Resume suspended Docker infrastructure containers"
	@echo "   make restart            - Gracefully restart local infrastructure containers"
	@echo "   make down               - Stop infrastructure containers (SAFE: preserves volume data)"
	@echo "   make status             - Display container & health status"
	@echo "   make health             - Alias for status"
	@echo "   make logs               - Tail container logs"
	@echo "   make reset-data         - DESTRUCTIVE: Delete local database & cache volumes"
	@echo " Quality Gate Commands (S00.6):"
	@echo "   make format             - Auto-format source code with black"
	@echo "   make format-check       - Verify source code formatting compliance with black"
	@echo "   make lint               - Run static code linter with flake8"
	@echo "   make typecheck          - Perform static type checking with mypy"
	@echo "   make test               - Execute all automated unit & integration test suites"
	@echo "   make security           - Execute security test suite"
	@echo "   make secret-scan        - Run repository security secret scanner"
	@echo "   make architecture-check - Run architecture regression guard"
	@echo "   make demo               - Launch the Razorpay AI Commerce live interactive demo"
	@echo "   make check              - Master Quality Gate: Run all checks sequentially (FAIL-CLOSED)"
	@echo "   make clean              - Clean temporary build artifacts & caches"
	@echo "============================================================"

demo:
	@PYTHONPATH=. $(PYTHON) scripts/run_live_demo.py

preflight:
	@echo "Running local preflight environment checks..."
	@if [ ! -f .env ]; then \
		echo "[NOTICE] .env not found. Creating from .env.example..."; \
		cp .env.example .env; \
	fi
	@echo "[✓] Environment file .env present."
	@if command -v docker >/dev/null 2>&1; then \
		echo "[✓] Docker CLI detected."; \
		docker compose config >/dev/null 2>&1 && echo "[✓] docker-compose.yml configuration valid." || echo "[!] Warning: docker compose config failed."; \
	else \
		echo "[!] Docker CLI not available in current environment. Static validation mode active."; \
	fi
	@echo "[✓] Preflight check completed."

config-check: preflight
	@PYTHONPATH=. $(PYTHON) -c "from apps.api.config import config_check_summary; print(config_check_summary())"

install:
	@echo "Installing local quality gate toolchain dependencies..."
	@$(PYTHON) -m pip install --quiet --break-system-packages black flake8 mypy 2>/dev/null || $(PYTHON) -m pip install --quiet black flake8 mypy
	@echo "[✓] Toolchain dependencies (black, flake8, mypy) installed successfully."

dev: up

up: preflight
	@if command -v docker >/dev/null 2>&1; then \
		docker compose up -d; \
	else \
		echo "[!] Docker CLI unavailable. Cannot launch containers in this environment."; \
		exit 1; \
	fi

stop:
	@if command -v docker >/dev/null 2>&1; then \
		docker compose stop; \
	else \
		echo "[!] Docker CLI unavailable."; \
		exit 1; \
	fi

start:
	@if command -v docker >/dev/null 2>&1; then \
		docker compose start; \
	else \
		echo "[!] Docker CLI unavailable."; \
		exit 1; \
	fi

restart:
	@if command -v docker >/dev/null 2>&1; then \
		docker compose restart; \
	else \
		echo "[!] Docker CLI unavailable."; \
		exit 1; \
	fi

down:
	@if command -v docker >/dev/null 2>&1; then \
		docker compose down; \
		echo "[✓] Infrastructure containers stopped. Persistent volumes preserved."; \
	else \
		echo "[!] Docker CLI unavailable."; \
		exit 1; \
	fi

status:
	@if command -v docker >/dev/null 2>&1; then \
		docker compose ps; \
	else \
		echo "[!] Docker CLI unavailable in current environment."; \
	fi

health: status

logs:
	@if command -v docker >/dev/null 2>&1; then \
		docker compose logs -f; \
	else \
		echo "[!] Docker CLI unavailable."; \
		exit 1; \
	fi

reset-data:
	@echo "============================================================"
	@echo " WARNING: DESTRUCTIVE OPERATION"
	@echo " This command will PERMANENTLY DELETE local PostgreSQL & Redis volumes:"
	@echo "   - mandate-gateway-postgres-data"
	@echo "   - mandate-gateway-redis-data"
	@echo "============================================================"
	@read -p "Are you sure you want to delete all local development data? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		if command -v docker >/dev/null 2>&1; then \
			docker compose down -v; \
			echo "[✓] Local database and cache volumes deleted."; \
		else \
			echo "[!] Docker CLI unavailable."; \
			exit 1; \
		fi \
	else \
		echo "[CANCELLED] Data reset operation aborted."; \
	fi

format:
	@echo "Running code auto-formatter (black)..."
	@PYTHONPATH=. $(PYTHON) -m black apps/ tests/ scripts/

format-check:
	@echo "Running formatting compliance check (black --check)..."
	@PYTHONPATH=. $(PYTHON) -m black --check apps/ tests/ scripts/

lint:
	@echo "Running static code linter (flake8)..."
	@PYTHONPATH=. $(PYTHON) -m flake8 apps/ scripts/ tests/

typecheck:
	@echo "Running static type checker (mypy)..."
	@PYTHONPATH=. $(PYTHON) -m mypy apps/ scripts/ tests/

test:
	@echo "Running automated test suites..."
	@PYTHONPATH=. $(PYTHON) -m unittest discover -s tests -p "test_*.py" -v

security:
	@echo "Running security test suite..."
	@PYTHONPATH=. $(PYTHON) -m unittest discover -s tests/security -p "test_*.py" -v

secret-scan:
	@echo "Running repository security secret scanner..."
	@PYTHONPATH=. $(PYTHON) scripts/secret_scan.py

architecture-check:
	@echo "Running architecture regression guard..."
	@PYTHONPATH=. $(PYTHON) scripts/architecture_check.py

check: preflight config-check format-check lint typecheck test security secret-scan architecture-check
	@echo "============================================================"
	@echo " [✓] ALL S00.6 QUALITY GATE CHECKS PASSED CLEANLY!"
	@echo "============================================================"

clean:
	@echo "Cleaning temporary files and cache directories..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "[✓] Clean completed."
