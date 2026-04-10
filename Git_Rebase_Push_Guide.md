# Git Rebase And Push Guide

This file records the safe command sequence for resolving a rejected push when remote `main` contains commits that local `main` does not yet have.

## 1) Quick Command List

Use this section as the concise reference.

```bash
# Check branch state
git status
git status --short --branch

# Download remote updates safely
git fetch origin

# Rebase local work onto remote main
git pull --rebase origin main

# Show unresolved conflict files
git diff --name-only --diff-filter=U

# Inspect one conflicted file
git diff -- apps/api/index.js

# Stage a resolved file
git add apps/api/index.js

# Continue the active rebase without opening an editor
GIT_EDITOR=true git rebase --continue

# Abort the active rebase safely
git rebase --abort

# Normal commit flow when no rebase is active
git add <file>
git commit -m "message"

# Push after verification
git push origin main

# Short help without pager problems
git push -h
```

What each group is for:

- `git status`, `git status --short --branch` check branch state and whether a rebase is active.
- `git fetch origin`, `git pull --rebase origin main` update local history safely without overwriting remote work.
- `git diff --name-only --diff-filter=U`, `git diff -- apps/api/index.js` debug rebase conflicts.
- `git add apps/api/index.js`, `GIT_EDITOR=true git rebase --continue` finish a resolved conflict.
- `git rebase --abort` cancels the rebase safely if the conflict resolution should be discarded.
- `git add <file>`, `git commit -m "message"` are for normal local commits when no rebase is active.
- `git push origin main` publishes the verified branch.

## 2) Why The Push Error Happened

When Git shows:

```text
! [rejected] main -> main (fetch first)
error: failed to push some refs
```

the meaning is:

- local `main` has commits that are not on the remote branch
- remote `main` also has commits that are not in the local branch
- Git blocks the push to avoid overwriting remote history

This is a non-fast-forward push rejection.

## 3) Safe Command Sequence

Use this sequence when the branch is clean and no rebase is already running:

```bash
# Check local branch state
git status

# Download remote commits without changing local files
git fetch origin

# Rebase local commits on top of remote main
git pull --rebase origin main

# Push after rebase succeeds
git push origin main
```

## 4) If A Rebase Is Already In Progress

Check the current state:

```bash
git status
```

If Git reports:

```text
interactive rebase in progress
```

do not run `git pull` again.

Instead:

```bash
# Show unresolved files
git diff --name-only --diff-filter=U

# Inspect the conflict
git diff -- apps/api/index.js
```

After the conflict markers are removed and the file is resolved:

```bash
# Mark the file as resolved
git add apps/api/index.js

# Continue the current rebase
GIT_EDITOR=true git rebase --continue
```

If the rebase must be canceled safely:

```bash
git rebase --abort
```

## 5) Conflict Resolution Principle

When resolving a conflict manually:

- preserve valid code from the remote branch
- preserve valid new feature code from the local branch
- remove `<<<<<<<`, `=======`, and `>>>>>>>`
- stage the resolved file with `git add`

Do not use `git checkout --ours` or `git checkout --theirs` unless one entire side should be discarded.

## 6) Verify Before Pushing

After the rebase completes, verify the application before pushing:

```bash
# Task 2.2 tests
pytest task_2_2_tests -q

# Task 2.4 tests
pytest task_2_4_tests -q

# Full integration check
bash scripts/task_2_all_check.sh
```

Expected result:

- Task 2.2 pytest passes
- Task 2.4 pytest passes
- the all-in-one script completes without errors

## 7) Final Safe Push

When verification is complete:

```bash
git status
git push origin main
```

Expected `git status` result:

```text
## main...origin/main [ahead 1]
```

Expected `git push` result:

```text
To github.com:...
   <old>..<new>  main -> main
```

## 8) If `git push --help` Gets Suspended

If the terminal shows:

```text
zsh: suspended  git push --help
```

the help pager was suspended, commonly by `Ctrl+Z`.

Use:

```bash
# Resume the suspended job
fg
```

or:

```bash
# Show short help without the pager
git push -h
```

## 9) Shortest Safe Path

If the branch is clean and no rebase is already running:

```bash
git fetch origin
git pull --rebase origin main
git push origin main
```

## 10) Single-Terminal Demo Sequence

Use this sequence to start the backend stack, run the pytest suites, and show the endpoint checks in one terminal. This assumes Docker Desktop and VS Code are already open.

```bash
# Start PostgreSQL in Docker
docker compose up -d postgres

# Initialize the database schema
docker compose run --rm etl python -c "from db import init_db; init_db()"

# Start the API in the background and capture logs
DATABASE_URL=postgres://user:password@localhost:5432/hypecheck npm run dev:api > /tmp/hypecheck-api.log 2>&1 &
API_PID=$!

# Give the API a moment to start
sleep 5

# Show health response
curl -s -w '\nstatus=%{http_code}\n' http://localhost:3000/

# Run Task 2.2 pytest
pytest task_2_2_tests -q

# Run Task 2.2 endpoint script
bash scripts/task_2_2_check.sh

# Run Task 2.4 endpoint script
bash scripts/task_2_4_check.sh

# Run the combined checker before Task 2.4 pytest
python3 task_2_4_tests/main.py

# Run Task 2.4 pytest last
pytest task_2_4_tests -q

# Run the all-in-one integration script
bash scripts/task_2_all_check.sh
```

What this demonstrates:

- PostgreSQL starts successfully
- the API boots on `localhost:3000`
- Task 2.2 tests pass
- Task 2.4 tests pass
- the endpoint scripts return valid responses

## 11) Optional Cleanup After Demo

Use this sequence to stop the local demo processes:

```bash
# Stop the background API started in the same shell
kill "$API_PID"

# Stop Docker services
docker compose down
```

## 12) If The API Does Not Start

Use these checks:

```bash
# Read the API startup log
cat /tmp/hypecheck-api.log

# Check whether port 3000 is already in use
lsof -nP -iTCP:3000 -sTCP:LISTEN

# Check Docker containers
docker compose ps
```
