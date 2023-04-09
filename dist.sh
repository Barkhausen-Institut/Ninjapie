#!/bin/sh

case "$1" in
    test)
        cd tests && ./run.sh
        ;;

    cov)
        cd tests && ./runcov.sh
        ;;

    lint)
        disabled="C0115,C0116,C0114,W0212,W0622,R0903,R0913,R0904,R0902,C0209"
        # disable unsubscriptable-object error for Python < 3.9 as this seems to be a false positive
        if [ "$(python3 -c 'import sys; print(sys.version_info.minor)')" -lt 9 ]; then
            disabled="$disabled,E1136"
        fi
        res=0
        pylint --disable "$disabled" $(git ls-files 'ninjapie/*.py') || res=1
        ninjapiepath="$(dirname "$(readlink -f "$0")")/ninjapie"
        export PYTHONPATH="$ninjapiepath:$PYTHONPATH"
        pylint --disable "$disabled,R0801,W0621" $(git ls-files 'tests/*.py') || res=1
        exit $res
        ;;

    dist)
        python -m build
        rm -rf ninjapie.egg-info
        ;;

    upload)
        twine check dist/* && twine upload dist/*
        ;;

    patch|minor|major)
        bumpver update "--$1"
        ;;

    *)
        echo "Usage: $0 test|cov|lint|dist|upload|patch|minor|major" >&2
        exit 1
        ;;
esac
