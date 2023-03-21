#!/bin/bash

root=$(dirname "$(dirname "$(readlink -f "$0")")")
export PATH="$root:$PATH"

success=0
failed=0
while IFS= read -r -d '' d; do
    echo "Running test in \"$(basename "$d")\"..."

    if (
        cd "$d" && ninjapie -c || exit 1

        ninjapie -v || exit 1

        if [ "$(basename "$d")" != "rust" ] && [ "$(basename "$d")" != "rust-c" ]; then
            if [ "$(ninjapie -v 2>&1)" != "ninja: no work to do." ]; then
                echo "Expected no work, but got work to do."
                exit 1
            fi
        fi

        if [ "$(basename "$d")" != "shared-lib" ]; then
            if ! LD_LIBRARY_PATH=build:$LD_LIBRARY_PATH ./build/hello >/dev/null; then
                exit 1
            fi
        fi
    ); then
        success=$((success + 1))
        /bin/echo -e "\e[1mSUCCESS\e[0m"
    else
        failed=$((failed + 1))
        /bin/echo -e "\e[1mFAILED\e[0m"
    fi
done < <(find . -mindepth 1 -maxdepth 1 -type d -print0)

printf "\nIn total: "
if [ $failed -eq 0 ]; then
    /bin/echo -n -e "\e[1;32m"
else
    /bin/echo -n -e "\e[1;31m"
fi
printf "%d of %d tests successful\n" $success $((success + failed))
/bin/echo -e "\e[0m"
