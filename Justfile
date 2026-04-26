
# List commands
default:
  @just --list

# Set up poetry/python environment
init:
  pre-commit install
  pre-commit autoupdate
  poetry install

# Run linters linters
lint:
  uv run -- ruff check .
  uv run -- ruff format --diff | bat -l diff -p
  uv run -- mypy cade_task

# Run pytest with supplied options
@test *options:
  uv run -- pytest --cov=cade_task {{options}}
  uv run -- coverage html

# Run linters in fix mode
fix:
  uv run -- ruff format
  uv run -- ruff check . --fix

# Build docs (`just docs live` for auto-rebuild)
docs *type:
  uv run -- {{ if type == "live" { "sphinx-autobuild" } else { "sphinx-build" } }} -b html docs docs/_build/html

# Enter virtual environment
shell:
  # This is busted
  poetry shell

# Publish package to PyPI
publish:
  # Using PyPI token from POETRY_PYPI_TOKEN_PYPI
  # Build package
  poetry build
  # Publish package
  poetry publish

# Launch ipython in environment
ipython:
  uv run -- ipython

# Aliases
alias i := ipython
alias l := lint
alias t := test
