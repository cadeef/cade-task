# Task (cade-task)

Task is a macOS CLI for project-linked Reminders lists. It wraps Reminders.app through
[`reminders-cli`](https://github.com/keith/reminders-cli) and makes it easy to manage tasks
from the terminal while also surfacing TODO-style comments from your codebase in `task list`.

## Quick Start

### Install

Install with [`pipx`](https://pipx.pypa.io/stable/):

```sh
pipx install cade-task
```

Or with [`uv`](https://docs.astral.sh/uv/):

```sh
uv tool install cade-task
```

### Requirements

Task is intended for macOS and depends on
[`reminders-cli`](https://github.com/keith/reminders-cli) being installed and available on your
`PATH`.

### Set your project directory

Export `TASK_PROJECT_DIR` for your shell environment:

```sh
export TASK_PROJECT_DIR="${HOME}/awesome_stuff"
```

If your project lives at `~/awesome_stuff/my-app`, Task will infer the Reminders list `my-app`
when you run commands from that directory.

### Try it

```sh
$ task list
                                 Tasks
┌───────┬──────────────────────────────────────────────────────────────┐
│ Index │ Task                                                         │
├───────┼──────────────────────────────────────────────────────────────┤
│ 0     │ Refactor code, all of it                                     │
│ 1     │ Add testing to generator                                     │
│       │ TODO: handle empty API responses (src/client.py:57)          │
│       │ PERF: cache parsed reminders output (cade_task/lib.py:91)    │
└───────┴──────────────────────────────────────────────────────────────┘
```

`task list` shows both Reminders tasks and TODO-style comments discovered in the current
project.

## How Project Detection Works

Task uses your current working directory and `TASK_PROJECT_DIR` to infer which Reminders list to
use.

For example:

```text
TASK_PROJECT_DIR=/Users/cade/code
cwd=/Users/cade/code/groceries/docs
```

In that case, Task uses the Reminders list `groceries`.

If you are outside your project tree, you can always choose a list explicitly:

```sh
task list --list groceries
```

## TODO Comment Support

When you run `task list`, Task also scans the current project for TODO-style comment markers and
shows them inline with file and line-number context.

Supported markers: `TODO:`, `FIXME:`, `ISSUE:`, `HACK:`, `TIP:`, `INFO:`, `PERF:`, `TEST:`,
`WARN:`, `XXX:`, and `BUG:`.

Only markers with a trailing colon are recognized. For example, `TODO:` matches, but `TODO`
without a colon does not.

If the inferred Reminders list does not exist but matching project comments are found, `task list`
still shows the local comment items instead of exiting immediately.

## Troubleshooting

If `task` fails to start after install:

- Run `task --version` to confirm the command is on your `PATH`.
- Make sure `reminders` from `reminders-cli` is installed and available.
- If you installed an older broken release from PyPI, upgrade to the latest version.

If Task cannot infer the current project:

- Check that `TASK_PROJECT_DIR` points to the parent directory that contains your projects.
- Run commands from somewhere under that directory, or pass `--list` explicitly.

Check out [usage](https://task.cade.pro/usage.html) or `--help` for more commands.

## Caveats

- Task wraps [Keith Smiley’s reminders-cli](https://github.com/keith/reminders-cli). Task is
  intended as a backend-agnostic wrapper that standardizes use without being tied to a specific
  implementation. I don’t want to retrain muscle memory if a new killer app comes along.

## License

This project is distributed under an MIT license, see [LICENSE](https://github.com/cadeef/cade-task/blob/main/LICENSE) for more information.

Made it this far? **You deserve a hug.**
