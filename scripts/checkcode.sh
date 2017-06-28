#!/bin/sh

ERROR=0

echo "Checking with pep8"
pep8 $1/*.py $1/*/*.py || ERROR=$(expr $ERROR + 1)

echo "Checking with pylint"
pylint $1/*.py $1/*/*.py || ERROR=$(expr $ERROR + 2)

exit $ERROR
