# Usage

Commands are aware of project context where available. Task assumes you store all of your projects in the same directory (defined with `--project-dir`), shell aliases are your friend.

Short flags exist for all options, but the long version is used here for clarity.

## List Tasks

List tasks for your current project:

```sh
task list
```

`task list` combines two sources:

- Reminders tasks from the active list
- TODO-style project comments found under the current working directory

Supported comment markers are:

- `TODO:`
- `FIXME:`
- `ISSUE:`
- `HACK:`
- `TIP:`
- `INFO:`
- `PERF:`
- `TEST:`
- `WARN:`
- `XXX:`
- `BUG:`

Code comments are shown inline with their file path and line number at the end of the row. For example:

```text
TODO: tighten parser validation (src/parser.py:42)
WARN: mutates shared state (cade_task/cli.py:88)
```

If the matching Reminders list does not exist but project comments are found, Task will still show the local comment items instead of exiting immediately.

Not in your project directory? No problem, specify the list you’d like to interact with:

```sh
task list --list <yourgloriouslist>
```

The list selection convention is consistent throughout the app.

## Add a Task

```sh
task add A glorious task that should be completed
```

Don’t worry about quotes unless you’re doing something funky, task will glue the arguments together for you.

## Complete Tasks

Complete one or more tasks:

```sh
task complete 6 1 3
```

Tasks are completed in reverse numerical order (10...1) to avoid re-parsing the task list after each task is completed.

## Open Reminders.app

Conveniently open (or bring to the foreground) Reminders.app:

```sh
task open
```

______________________________________________________________________

Additional usage information is available via `--help` on the command line.

## Shell Aliases

The defaults may not work for you. Shell aliases are cheap and easy. Define a different project directory from bash:

```sh
export TASK_PROJECT_DIR="${HOME}/myprettyneatprojectdir"
# List tasks in current project
alias t="task list"
# Add task in current project
alias ta="task add"
# Complete task(s) in current project
alias tc="task complete"
# List task lists
alias tl="task lists"
# Open Reminders.app
alias to="task open"
```

Tweak until your heart is content without monkeying yet another config file.
