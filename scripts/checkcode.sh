#!/bin/sh

ERROR=0

if [ $# != 1 ]; then
    echo "Error: Please provide a path as the argument to this script!"
    exit 1
fi

echo "Checking with pycodestyle"
pycodestyle --ignore=W503,W606 "$1"/*.py "$1"/*/*.py || ERROR=$((ERROR + 1))

echo "Checking with flake8"
flake8 "$1" || ERROR=$((ERROR + 2))

echo "Checking with doc8"
doc8  "$1"/docs --ignore-path "$1"/docs/_build || ERROR=$((ERROR + 4))

echo "Checking with shellcheck"
shellcheck "$1"/kas-container "$1"/scripts/release.sh "$1"/scripts/checkcode.sh "$1"/container-entrypoint || ERROR=$((ERROR + 8))

exit $ERROR
