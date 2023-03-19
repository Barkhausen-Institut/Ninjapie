#!/bin/bash

root=$(dirname "$(dirname "$(readlink -f "$0")")")
export PATH="$root:$PATH"

export PYTHONDONTWRITEBYTECODE=1

dirs=()
while IFS= read -r -d '' d; do
    echo "Generating coverage for \"$(basename "$d")\"..."

    if (
        root=$(dirname "$(dirname "$(readlink -f "$0")")")
        export PYTHONPATH="$root:$PYTHONPATH"
        cd "$d"
        rm -rf build && mkdir -p build
        coverage run build.py || exit 1
        ninja -f build/build.ninja -v || exit 1
    ); then
        /bin/echo -e "\e[1mSUCCESS\e[0m"
    else
        /bin/echo -e "\e[1mFAILED\e[0m"
    fi

    dirs=("${dirs[@]}" "$d/.coverage")
done < <(find . -mindepth 1 -maxdepth 1 -type d -print0)

coverage combine "${dirs[@]}"
coverage html -d ../coverage
