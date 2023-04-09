#!/bin/bash

root=$(dirname "$(dirname "$(readlink -f "$0")")")

ninjapie() {
    python3 "$root/ninjapie/__main__.py" "$@"
}

success=0
failed=0
while IFS= read -r -d '' d; do
    echo "Running test in \"$(basename "$d")\"..."

    if (
        cd "$d" && ninjapie clean || exit 1

        ninjapie -- -v || exit 1

        case "$(basename "$d")" in
            rust|rust-c) ;;
            *)
                if [ "$(ninjapie -- -v 2>&1)" != "ninja: no work to do." ]; then
                    echo "Expected no work, but got work to do."
                    exit 1
                fi
                ;;
        esac

        case "$(basename "$d")" in
            shared-lib|latex) ;;
            *)
                if ! LD_LIBRARY_PATH=build:$LD_LIBRARY_PATH ./build/hello >/dev/null; then
                    exit 1
                fi
                ;;
        esac
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
    res=0
else
    /bin/echo -n -e "\e[1;31m"
    res=1
fi
printf "%d of %d tests successful\n" $success $((success + failed))
/bin/echo -e "\e[0m"

exit $res
