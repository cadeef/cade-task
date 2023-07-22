set dotenv-load

# List commands
default:
  @just --list

# Set up poetry/python environment
init:
  poetry install

# Run linters linters
lint:
  poetry run ruff check .
  poetry run mypy cade_task
  poetry run black . --check

# Run pytest with supplied options
@test *options:
  poetry run pytest {{options}}

# Run linters in fix mode
fix:
  poetry run ruff check . --fix
  poetry run black .

# Enter virtual environment
shell:
  poetry shell

# Publish package to PyPI
publish:
  # Set PyPI Token
  -poetry config pypi-token.pypi $PYPI_API_TOKEN
  # Build package
  poetry build
  # Publish package
  poetry publish

# act shortcut
act *options:
  @act --container-daemon-socket $(docker context inspect --format '{{ "{{" }}.Endpoints.docker.Host{{ "}}" }}') {{options}}

boof:
  # Add searchable repo (probably don't want to do this with testpypi)
  # poetry source add testpypi https://test.pypi.org/simple/ --priority explicit
