#!/bin/bash

OLD_VERSION=${1:-}
NEW_VERSION=${2:-}

usage() {
    echo "$0: OLD_VERSION NEW_VERSION"
    echo ""
    echo "example:"
    echo "  $0 0.15.0 0.16.0"
}

if [ -z "$OLD_VERSION" ] || [ -z "$NEW_VERSION" ] ; then
    usage
    exit 1
fi

echo "$NEW_VERSION" > newchangelog
git shortlog "$OLD_VERSION".. >> newchangelog
cat CHANGELOG.md >> newchangelog

emacs newchangelog --eval "(text-mode)"

echo -n "All fine, ready to release? [y/N]"
read a
a=$(echo "$a" | tr '[:upper:]' '[:lower:]')
if [ "$a" != "y" ]; then
    echo "no not happy, let's stop doing the release"
    exit 1
fi

mv newchangelog CHANGELOG.md
sed -i "s,\(__version__ =\).*,\1 \'$NEW_VERSION\'," kas/__version__.py

git add CHANGELOG.md
git add kas/__version__.py

git commit -m "Release $NEW_VERSION"
git tag -s -m "Release $NEW_VERSION" "$NEW_VERSION"
git push --follow-tags

# http://peterdowns.com/posts/first-time-with-pypi.html
python setup.py sdist upload -r pypitest
python setup.py sdist upload -r pypi

authors=$(git shortlog -s "$OLD_VERSION".."$NEW_VERSION" | cut -c8- | paste -s -d, - | sed -e 's/,/, /g')
highlights=$(cat CHANGELOG.md | sed -e "/$OLD_VERSION/,\$d")

prolog=release-email.txt
echo \
"
Hi,

A new release $NEW_VERSION is available. A big thanks to all contributors:
$authors

Highlights in $highlights

Thanks,
Daniel

https://github.com/siemens/kas/releases/tag/$NEW_VERSION
https://hub.docker.com/r/kasproject/kas/

"> $prolog

git shortlog $OLD_VERSION..$NEW_VERSION >> $prolog

neomutt -s "[ANNOUNCE] Release $NEW_VERSION" kas-devel@googlegroups.com < $prolog
