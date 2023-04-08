#!/bin/sh

case "$1" in
    test)
        cd tests && ./run.sh
        ;;

    cov)
        cd tests && ./runcov.sh
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
        echo "Usage: $0 test|cov|dist|upload|patch|minor|major" >&2
        exit 1
        ;;
esac
