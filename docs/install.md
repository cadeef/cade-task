# Install

Task is distributed as a Python CLI. The two easiest ways to install are `pipx` or `uv`.

## Install with pipx

[`pipx`](https://pipx.pypa.io/stable/) installs Python CLI apps into isolated virtual environments and exposes them on your `PATH`.

```sh
pipx install cade-task
```

Upgrade later with:

```sh
pipx upgrade cade-task
```

## Install with uv

[`uv`](https://docs.astral.sh/uv/) can install CLI tools globally in a similar way:

```sh
uv tool install cade-task
```

Upgrade later with:

```sh
uv tool upgrade cade-task
```

## Verify the install

After installation, confirm the command is available:

```sh
task --version
```

## Next step

Set your project directory so `task` can infer the current Reminders list from your working directory:

```sh
export TASK_PROJECT_DIR="${HOME}/awesome_stuff"
```

Then try:

```sh
task list
```
