#!/bin/bash

OLD_VERSION=$(git describe --abbrev=0)
NEW_VERSION=$1

usage() {
    echo "$0: NEW_VERSION"
    echo ""
    echo "example:"
    echo "  $0 0.16.0"
}

if [ -z "$NEW_VERSION" ] ; then
    usage
    exit 1
fi

echo "$NEW_VERSION" > newchangelog
git shortlog "$OLD_VERSION".. >> newchangelog
cat CHANGELOG.md >> newchangelog

$EDITOR newchangelog

echo -n "All fine, ready to release? [y/N]"
read a
a=$(echo "$a" | tr '[:upper:]' '[:lower:]')
if [ "$a" != "y" ]; then
    echo "no not happy, let's stop doing the release"
    exit 1
fi

mv newchangelog CHANGELOG.md
sed -i "s,\(__version__ =\).*,\1 \'$NEW_VERSION\'," kas/__version__.py
sed -i "s,\(KAS_IMAGE_VERSION_DEFAULT=\).*,\1\"$NEW_VERSION\"," kas-container

git add CHANGELOG.md
git add kas/__version__.py
git add kas-container

git commit -m "Release $NEW_VERSION"
git tag -s -m "Release $NEW_VERSION" "$NEW_VERSION"
git push --follow-tags

python setup.py sdist upload -r pypi

authors=$(git shortlog -s "$OLD_VERSION".."$NEW_VERSION" | cut -c8- | paste -s -d, - | sed -e 's/,/, /g')
highlights=$(cat CHANGELOG.md | sed -e "/$OLD_VERSION/,\$d")

prolog=$PWD/release-email.txt
echo \
"Hi all,

A new release $NEW_VERSION is available. A big thanks to all contributors:
$authors

Highlights in $highlights

Thanks,
Jan

https://github.com/siemens/kas/releases/tag/$NEW_VERSION
https://github.com/orgs/siemens/packages/container/package/kas%2Fkas
https://github.com/orgs/siemens/packages/container/package/kas%2Fkas-isar

"> $prolog

git shortlog $OLD_VERSION..$NEW_VERSION >> $prolog

thunderbird -compose "subject=[ANNOUNCE] Release $NEW_VERSION,to=kas-devel@googlegroups.com,message=$prolog"
