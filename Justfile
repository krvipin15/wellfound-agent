# Automatically load .env file if it exists
set dotenv-load := true

# Display available commands with descriptions
default:
    @just --list --unsorted

## --- Setup & Configuration ---

# Install dependencies with uv and setup pre-commit hooks
env-setup:
    uv self update
    uv sync --all-groups --all-extras
    uvx detect-secrets scan > .secrets.baseline
    uv run pre-commit install --install-hooks -t pre-commit -t commit-msg -t pre-push
    @echo "success: Environment setup complete. Pre-commit hooks installed."

## --- Development & Maintenance ---

# Upgrade project lockfile dependencies
lock:
    uv lock --upgrade

# Update git pre-commit hook versions to latest
hooks-update:
    uv run pre-commit autoupdate
    sed -i 's|rev: v1$|rev: v1.50.3|' .pre-commit-config.yaml
    @echo "warning: Check https://github.com/crate-ci/typos/releases for the latest typos version — v1.50.3 was hardcoded above and may be stale"

# Run pre-commit checks across all staged/unstaged files
hooks-run:
    uv run pre-commit run --all-files

## --- Testing & Quality ---

# Run pytest test suite with coverage report
test:
    uv run pytest tests/ -v

## --- Documentation ---

# Serve the documentation site locally with live reload
docs-serve mkdocs_port="5050":
    uv run mkdocs serve -a 127.0.0.1:{{mkdocs_port}} --strict

# Publish the documentation to GitHub Pages
docs-deploy:
    uv run mkdocs gh-deploy -csm "Deploy the latest documentation" -b gh-pages --shell --force

## --- Application Execution ---

# Run the FastAPI application with uvicorn for development
serve:
    uv run uvicorn wellfound_agent.api.app:app --reload

## --- Temporal ---

# Start the local Temporal development server
temporal-up:
    podman compose up -d temporal

# Stop the local Temporal development server
temporal-down:
    podman compose down

# Open the Temporal Web UI in the default web browser
temporal-ui:
    xdg-open http://localhost:8233

# Start the Wellfound Temporal Worker
temporal-worker:
    python3 -m wellfound_agent.workflows.worker

# Start a Wellfound Workflow execution
temporal-run:
    uv run python -m wellfound_agent.workflows.client

## --- Cleanup ---

# Clean everything; cache, and logs
clean-all: clean-cache clean-logs

# Clean temporary Python, pytest, and build cache directories
clean-cache:
    find . -type d -regex ".*\(__pycache__\|\.pytest_cache\|\.ruff_cache\|\.mypy_cache\|\.pyright_cache\)" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    rm -rf .coverage htmlcov/ site/ dist/ build/ *.egg-info
    rm -f coverage.xml
    rm -rf browser_user_data/
    @echo "success: Cleaned all the cache"

# Clean the generated log files
clean-logs:
    sudo rm -f logs/*.log
    @echo "success: Cleaned log files in the logs directory."

# Clean podman containers, images, and volumes associated with the project
clean-container:
    podman-compose down --volumes --rmi all
    podman system prune -f
    @echo "success: Containers, volumes, and images cleaned."
