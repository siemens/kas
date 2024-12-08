#!/bin/sh
#
# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2024
#
# Authors:
#  Jan Kiszka <jan.kiszka@siemens.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

if [ -z "$1" ] || [ "$1" = "--help" ]; then
	echo "Usage: $0 kas[-isar]:<tag> [architecture]"
	exit 0
fi

TARGET=$(echo "$1" | sed 's/:.*//')
TAG=$(echo "$1" | sed 's/.*://')
ARCH=$2

ARCH_OPT=
PLATFORM_OPT=
if [ -n "$ARCH" ]; then
	ARCH_OPT="--arch $ARCH"
	PLATFORM_OPT="--platform linux/$ARCH"
fi

# shellcheck disable=SC2086
docker pull $PLATFORM_OPT "ghcr.io/siemens/kas/$TARGET:$TAG"
DEBIAN_TAG=$(docker image inspect --format '{{json .Config.Env}}' \
	     "ghcr.io/siemens/kas/$TARGET:$TAG" |
	     sed 's/.*DEBIAN_BASE_IMAGE_TAG=\([^"]\+\).*/\1/')
if [ -z "$DEBIAN_TAG" ]; then
	echo "Cannot determine base image of ghcr.io/siemens/kas/$TARGET:$TAG"
	exit 1
fi

GIT_REFSPEC="$TAG"
if [ "$GIT_REFSPEC" = "latest" ]; then
	GIT_REFSPEC=master
fi

# shellcheck disable=SC2086
"$(dirname "$0")/build-container.sh" $ARCH_OPT --target "$TARGET" \
	--tag repro-test --git-refspec "$GIT_REFSPEC" \
	--debian-tag "$DEBIAN_TAG" --clean || exit 1

echo ""

docker images --digests | grep "^REPOSITORY\|^ghcr.io/siemens/kas/${TARGET}[ ]*\($TAG\|repro-test\)"
printf "%b" "\nReproduction test "
if [ "$(docker images -q "ghcr.io/siemens/kas/$1")" = "$(docker images -q "ghcr.io/siemens/kas/$TARGET:repro-test")" ]; then
	printf "%b" "SUCCEEDED\n"
	docker rmi "ghcr.io/siemens/kas/$TARGET:repro-test" >/dev/null
else
	printf "%b" "FAILED\n"
fi
