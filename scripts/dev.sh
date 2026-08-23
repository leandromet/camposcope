#!/usr/bin/env bash
# Run `reflex run`, guaranteeing the backend dies with it.
#
# Reflex's dev-mode backend runs under uvicorn's --reload supervisor, which
# spawns a worker subprocess sharing the supervisor's own argv — inspecting the
# process tree during development showed parent and child BOTH listed as
# literally `reflex run --env dev`, indistinguishable by cmdline. That worker
# does not reliably die when the supervisor exits: `reflex.utils.processes
# .atexit_handler` only prints "Reflex app stopped." — it kills no subprocess.
#
# Confirmed empirically: five `reflex run` invocations launched across one
# session all left their uvicorn worker bound to :8021 (via SO_REUSEPORT, which
# is why each NEXT `reflex run` kept "succeeding" instead of failing loudly —
# the leak was silent until the port was full of zombies and a plain
# `fuser -k :8021/tcp`, which only signals whichever process currently holds
# the fd, stopped being enough to clear it).
#
# The fix does not depend on Reflex/uvicorn's own signal handling at all: this
# script puts the WHOLE `reflex run` process tree into its own process group
# (setsid) and kills that GROUP — supervisor and worker together — on every
# exit path: Ctrl+C, `kill`, or a normal exit.
set -euo pipefail
cd "$(dirname "$0")/.."

REFLEX_PID=""

cleanup() {
    # A negative PID to kill(1)/kill(2) means "the whole process group", which
    # is what actually reaches the uvicorn reload worker — a plain
    # `kill "$REFLEX_PID"` only ever reaches the supervisor.
    if [[ -n "$REFLEX_PID" ]]; then
        kill -TERM -- "-${REFLEX_PID}" 2>/dev/null || true
        sleep 1
        kill -KILL -- "-${REFLEX_PID}" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# setsid makes the new process its own session AND process-group leader, so
# its PID doubles as the PGID `cleanup` needs.
setsid .venv/bin/reflex run "$@" &
REFLEX_PID=$!
wait "$REFLEX_PID"
