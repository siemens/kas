#!/bin/sh

ERROR=0

if [ $# != 1 ]; then
    SRCDIR=$(dirname "$0")/..
else
    SRCDIR=$1
fi

echo "Checking with pycodestyle"
pycodestyle --ignore=W503,W606 "$SRCDIR"/*.py "$SRCDIR"/*/*.py || ERROR=$((ERROR + 1))

echo "Checking with flake8"
flake8 "$SRCDIR" || ERROR=$((ERROR + 2))

echo "Checking with doc8"
doc8  "$SRCDIR"/docs --ignore-path "$SRCDIR"/docs/_build --ignore D000 || ERROR=$((ERROR + 4))

echo "Checking with shellcheck"
shellcheck "$SRCDIR"/kas-container \
        "$SRCDIR"/scripts/release.sh \
        "$SRCDIR"/scripts/checkcode.sh \
        "$SRCDIR"/scripts/build-container.sh \
        "$SRCDIR"/scripts/reproduce-container.sh \
        "$SRCDIR"/container-entrypoint || ERROR=$((ERROR + 8))

exit $ERROR
