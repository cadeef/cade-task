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
  poetry run pytest --cov=cade_task {{options}}
  poetry run coverage html

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

docker_socket := `docker context inspect --format '{{.Endpoints.docker.Host}}'`
docker_status := `limactl ls --json | jq -r 'select(.name == "docker") | .status'`

# act shortcut
act *options:
  [[ {{docker_status}} == "Running" ]] || limactl start docker
  act --container-daemon-socket {{docker_socket}} {{options}}
