#!/bin/bash

root=$(dirname "$(dirname "$(readlink -f "$0")")")
export PATH="$root:$PATH"

while IFS= read -r -d '' d; do
    echo "Running test in \"$(basename "$d")\"..."

    if (
        cd "$d" && ninjapie -c || exit 1
        ninjapie -v || exit 1
        if [ "$(ninjapie -v 2>&1)" != "ninja: no work to do." ]; then
            echo "Expected no work, but got work to do."
            exit 1
        fi
        if ! LD_LIBRARY_PATH=build:$LD_LIBRARY_PATH ./build/hello >/dev/null; then
            exit 1
        fi
    ); then
        /bin/echo -e "\e[1mSUCCESS\e[0m"
    else
        /bin/echo -e "\e[1mFAILED\e[0m"
    fi
done < <(find . -mindepth 1 -maxdepth 1 -type d -print0)
