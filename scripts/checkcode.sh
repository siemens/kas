#!/bin/sh

ERROR=0

echo "Checking with pep8"
pep8 $1/*.py $1/*/*.py || ERROR=$(expr $ERROR + 1)

echo "Checking with pylint"
pylint $1/*.py $1/*/*.py || ERROR=$(expr $ERROR + 2)

echo "Checking with doc8"
doc8  $1/docs --ignore-path $1/docs/_build || ERROR=$(expr $ERROR + 4)

exit $ERROR
