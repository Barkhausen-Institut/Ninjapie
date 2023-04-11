#!/bin/bash

root=$(dirname "$(readlink -f "$(dirname -- "${BASH_SOURCE[0]}")")")

ninjapie() {
    python3 "$root/ninjapie/__main__.py" "$@"
}

clean() {
    ninjapie clean || exit 1
}

check_build() {
    NPDEBUG=1 ninjapie -- -v || exit 1
}

check_no_work() {
    if [ "$(NPDEBUG=1 ninjapie -- -v 2>&1)" != "ninja: no work to do." ]; then
        echo "Expected no work, but got work to do."
        exit 1
    fi
}

check_run() {
    if ! LD_LIBRARY_PATH=build:$LD_LIBRARY_PATH "$1" >/dev/null; then
        exit 1
    fi
}

check_error() {
    tmp=$(mktemp)
    NPDEBUG=1 ninjapie -- -v 2>&1 | tee "$tmp"
    [ "${PIPESTATUS[0]}" -ne 0 ] || exit 1
    grep "$1" "$tmp" &>/dev/null || exit 1
    rm -f "$tmp"
}
