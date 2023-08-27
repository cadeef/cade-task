# Task (cade-task)

Task is a light CLI wrapper around Reminders.app ([reminders-cli](https://github.com/keith/reminders-cli)) with sane defaults to remove friction from GTD.

## Quick Start

### Install

[pipx](https://pypa.github.io/pipx/):

```sh
pipx install cade-task
```

More [install options](https://task.cade.pro/install.html) availble.

### Set your project directory

Export `TASK_PROJECT_DIR` for your shell environment:

```sh
export TASK_PROJECT_DIR="${HOME}/awesome_stuff"
```

### Go

```sh
$ task list
               Tasks
┌───┬─────────────────────────────┐
│ 0 │ Refactor code, all of it    │
│ 1 │ Add testing to generator    │
│ 2 │ Push to prod Friday evening │
└───┴─────────────────────────────┘
```

Check out [usage](https://task.cade.pro/usage.html) or `--help` for more commands.

## Caveats

- Task wraps [Keith Smiley’s reminders-cli](https://github.com/keith/reminders-cli). Task is intended as a backend-agnostic wrapper that standardizes use without being tied to a specific implementation— I don’t want to retrain muscle memory if a new killer app comes along.

## License

This project is distributed under an MIT license, see [LICENSE](https://github.com/cadeef/cade-task/blob/main/LICENSE) for more information.

Made it this far? **You deserve a hug.**
