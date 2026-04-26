# Task (cade-task)

Task is a light CLI wrapper around Reminders.app ([reminders-cli](https://github.com/keith/reminders-cli)) with sane defaults to remove friction from GTD.

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

More [install options](https://task.cade.pro/install.html) available.

### Set your project directory

Export `TASK_PROJECT_DIR` for your shell environment:

```sh
export TASK_PROJECT_DIR="${HOME}/awesome_stuff"
```

### Go

```sh
$ task list
                           Tasks
┌───────┬──────────────────────────────────────────────────────┐
│ Index │ Task                                                 │
├───────┼──────────────────────────────────────────────────────┤
│ 0     │ Refactor code, all of it                             │
│ 1     │ Add testing to generator                             │
│       │ TODO: handle empty API responses (src/client.py:57)  │
│       │ PERF: cache parsed reminders output (cade_task/lib.py:91) │
└───────┴──────────────────────────────────────────────────────┘
```

`task list` shows both Reminders tasks and TODO-style comments discovered in the current project. Supported markers include `TODO:`, `FIXME:`, `ISSUE:`, `HACK:`, `TIP:`, `INFO:`, `PERF:`, `TEST:`, `WARN:`, `XXX:`, and `BUG:`.

Check out [usage](https://task.cade.pro/usage.html) or `--help` for more commands.

## Caveats

- Task wraps [Keith Smiley’s reminders-cli](https://github.com/keith/reminders-cli). Task is intended as a backend-agnostic wrapper that standardizes use without being tied to a specific implementation— I don’t want to retrain muscle memory if a new killer app comes along.

## License

This project is distributed under an MIT license, see [LICENSE](https://github.com/cadeef/cade-task/blob/main/LICENSE) for more information.

Made it this far? **You deserve a hug.**
