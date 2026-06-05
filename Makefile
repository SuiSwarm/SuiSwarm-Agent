# SuiSwarm Agent — common developer tasks.
# Uses `uv`; falls back to plain pip is left to the developer.

.PHONY: help install dev lock lint format type test cov check run serve docker up clean

help:
	@echo "Targets: install dev lock lint format type test cov check run serve docker up clean"

install:
	uv pip install -e .

dev:
	uv pip install -e ".[dev]"

lock:
	uv lock

lint:
	ruff check .

format:
	ruff format .

type:
	mypy

test:
	pytest

cov:
	pytest --cov

check: lint type test  ## the same gate CI runs

run:
	python -m suiswarm_agent chat

serve:
	uvicorn suiswarm_agent.interfaces.api.app:app --reload --port 8000

docker:
	docker build -t suiswarm-agent:latest .

up:
	docker compose up --build

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
