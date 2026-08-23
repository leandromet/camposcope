#!/usr/bin/env bash
# Force-free Camposcope's dev ports, whatever put something there.
#
# scripts/dev.sh (its own comment has the full story) prevents this going
# forward; this script is the recovery path for anything already leaked —
# including processes started before dev.sh existed, or started some other
# way (an editor's run button, a stray `nohup reflex run &`, ...).
#
# Uses fuser rather than pkill on a name pattern: reflex's backend worker is
# indistinguishable from its supervisor by cmdline (see dev.sh), so the only
# reliable handle is "whatever currently holds this port's listening socket".
set -euo pipefail

FRONTEND_PORT="${PORT:-3020}"
BACKEND_PORT="${BACKEND_PORT:-8021}"

for port in "$FRONTEND_PORT" "$BACKEND_PORT"; do
    if fuser "${port}/tcp" >/dev/null 2>&1; then
        echo "stopping process(es) on :${port}"
        fuser -k "${port}/tcp" 2>/dev/null || true
    fi
done

sleep 1

# fuser -k only signals whoever holds the fd AT THAT INSTANT — if several
# processes were bound via SO_REUSEPORT (exactly how this leak compounded
# originally), one round can miss the others. Loop until both ports are
# actually clear, not just until fuser was asked once.
for _ in 1 2 3 4 5; do
    still_bound=0
    for port in "$FRONTEND_PORT" "$BACKEND_PORT"; do
        if fuser "${port}/tcp" >/dev/null 2>&1; then
            still_bound=1
            fuser -k "${port}/tcp" 2>/dev/null || true
        fi
    done
    [[ "$still_bound" -eq 0 ]] && break
    sleep 1
done

if fuser "${FRONTEND_PORT}/tcp" >/dev/null 2>&1 || fuser "${BACKEND_PORT}/tcp" >/dev/null 2>&1; then
    echo "warning: could not fully clear :${FRONTEND_PORT} / :${BACKEND_PORT}" >&2
    exit 1
fi
echo "ports ${FRONTEND_PORT} and ${BACKEND_PORT} are free"
