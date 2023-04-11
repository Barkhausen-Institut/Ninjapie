#!/bin/bash

root=$(dirname "$(dirname "$(readlink -f "$0")")")
export PATH="$root:$PATH"

export PYTHONDONTWRITEBYTECODE=1

success=0
failed=0
dirs=()
while IFS= read -r -d '' d; do
    echo "Generating coverage for \"$(basename "$d")\"..."

    if (
        root=$(dirname "$(dirname "$(readlink -f "$0")")")
        export PYTHONPATH="$root:$PYTHONPATH" NPBUILD=build
        cd "$d"
        rm -rf build && mkdir -p build
        NPDEBUG=1 coverage run build.py
        if [[ ! "$(basename "$d")" =~ error-* ]]; then
            [ $? -eq 0 ] || exit 1
            ninja -f build/build.ninja -v || exit 1
        fi
    ); then
        success=$((success + 1))
        /bin/echo -e "\e[1mSUCCESS\e[0m"
    else
        failed=$((failed + 1))
        /bin/echo -e "\e[1mFAILED\e[0m"
    fi

    dirs=("${dirs[@]}" "$d/.coverage")
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

coverage combine "${dirs[@]}"
coverage html -d ../coverage

exit $res
