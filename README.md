# Task (cade-task)

Task is a light CLI wrapper around Reminders.app ([reminders-cli](https://github.com/keith/reminders-cli)) that unifies use with dead-simple, sane defaults to remove friction from GTD.

## Install

[pipx](https://pypa.github.io/pipx/):

```
pipx install cade-task
```

[brew](https://brew.sh/):

*Building bottles of python modules is flaky, not currently maintained*

```
brew install cadeef/tap/cade-task
```

## Usage

Commands are aware of project context where available. Task assumes you store all of your projects in the same directory (defined with `—-project-dir`), shell aliases are your friend.

Short flags exist for all options, but the long version is used here for clarity.

### List Tasks

List tasks for your current project:

```
task list
```

Not in your project directory? No problem, specify the list you’d like to interact with:

```
task list —-list <yourgloriouslist>
```

The list selection convention is consistent throughout the app.

### Add a Task

```
task add A glorious task that should be completed
```

Don’t worry about quotes unless you’re doing something funky, task will glue the arguments together for you.

### Complete Tasks

Complete one or more tasks:

```
task complete 6 1 3
```

Tasks are completed in reverse numerical order (10...1) to avoid re-parsing the task list after each task is completed.

### Open Reminders.app

Conveniently open (or bring to the foreground) Reminders.app:

```
task open
```

______________________________________________________________________

Additional usage information is available via `—-help` on the command line.

### Shell Aliases

The defaults may not work for you. Shell aliases are cheap and easy. Define a different project directory from bash:

```bash
TASK_PROJECT_DIR=“${HOME}/myprettyneatprojectdir”
# List tasks in current project
alias t=“task -d ${TASK_PROJECT_DIR} list”
# Add task in current project
alias ta=“task -d ${TASK_PROJECT_DIR} add”
# Complete task(s) in current project
alias tc=“task -d ${TASK_PROJECT_DIR} complete”
# Sync TODO|FIXME in current project
alias tsync=“task -d ${TASK_PROJECT_DIR} sync”
# List task lists
alias tl=“task lists”
# Open Reminders.app
alias to=“task open”
```

Tweak until your heart is content without monkeying yet another config file.

## Caveats

- Task wraps [Keith Smiley’s reminders-cli](https://github.com/keith/reminders-cli). Task is intended as a backend-agnostic wrapper that standardizes use without being tied to a specific implementation— I don’t want to retrain muscle memory if a new killer app comes along.

## License

This project is distributed under an MIT license, see [LICENSE](https://github.com/cadeef/cade-task/blob/main/LICENSE) for more information.

Made it this far? **You deserve a hug.**
