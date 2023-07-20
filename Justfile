# List commands
default:
  @just --list

# Run pre-commit linters
@lint:
  SKIP=poetry-check,poetry-lock,pytest pre-commit run -a

# Run pytest with supplied options
@test *options:
  poetry run pytest {{options}}
