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

# This needs to be aligned with .github/actions/docker-init/action.yml
BUILDKIT="moby/buildkit:v0.16.0"

usage()
{
	DEFAULT_DEBIAN_TAG=$(grep -m 1 'ARG DEBIAN_TAG=' "$(dirname "$0")/../Dockerfile" |
			     sed 's/.*DEBIAN_TAG=\(.*\)-\(.*\)/\1-<LATEST>-\2/')

	printf "%b" "Usage: $0 [OPTIONS]\n"
	printf "%b" "\nOptional arguments:\n"
	printf "%b" "--arch\t\tBuild for specified architecture, rather than the native one\n"
	printf "%b" "--clean\t\tRemove local images (ghcr.io/siemens/kas/TARGET:TAG) before\n" \
		    "\t\tstarting the build and do not use image cache\n"
	printf "%b" "--debian-tag\tUse specified tag for Debian base image\n" \
		    "\t\t(default=$DEFAULT_DEBIAN_TAG)\n"
	printf "%b" "--git-refspec\tUse specified revision/branch of kas repository (default=HEAD)\n"
	printf "%b" "--tag\t\tTag container with specified name (default=next)\n"
	printf "%b" "--target\tBuild specified target(s) (default=\"kas kas-isar\")\n"
}

build_image()
{
	IMAGE_NAME="ghcr.io/siemens/kas/$1:$TAG"

	OLD_IMAGE_ID=$(docker images -q "$IMAGE_NAME" 2>/dev/null)

	PLATFORM_OPT=
	if [ -n "$ARCH" ]; then
		PLATFORM_OPT="--platform linux/$ARCH"
	fi
	NOCHACHE_OPT=
	if [ "$CLEAN" = y ]; then
		NOCHACHE_OPT="--no-cache"
	fi
	# shellcheck disable=SC2086
	if ! docker buildx build --build-arg SOURCE_DATE_EPOCH="$(git log -1 --pretty=%ct)" \
			--output type=docker,rewrite-timestamp=true \
			--tag "$IMAGE_NAME" --build-arg DEBIAN_TAG="$DEBIAN_TAG" \
			--target "$1" $PLATFORM_OPT $NOCHACHE_OPT .; then
		echo "Build failed!"
		return 1
	fi

	if [ -n "$OLD_IMAGE_ID" ]; then
		if [ "$(docker images -q "$IMAGE_NAME")" = "$OLD_IMAGE_ID" ]; then
			echo "Reproduced identical image $IMAGE_NAME $OLD_IMAGE_ID"
		else
			echo "Deleting old image $OLD_IMAGE_ID"
			docker rmi "$OLD_IMAGE_ID"
		fi
	fi

	return 0
}

ARCH=
CLEAN=
DEBIAN_TAG=
GIT_REFSPEC=HEAD
TARGETS=
TAG=next
while [ $# -gt 0 ]; do
	case "$1" in
	--arch)
		shift
		ARCH="$1"
		;;
	--clean)
		CLEAN=y
		;;
	--debian-tag)
		shift
		DEBIAN_TAG="$1"
		;;
	--git-refspec)
		shift
		GIT_REFSPEC="$1"
		;;
	--tag)
		shift
		TAG="$1"
		;;
	--target)
		shift
		TARGETS="$TARGETS $1"
		;;
	*)
		usage
		exit 1
	esac
	shift
done

TARGETS="${TARGETS:-kas kas-isar}"

if [ -z "$DEBIAN_TAG" ]; then
	DEBIAN_RELEASE=$(grep -m 1 'ARG DEBIAN_TAG=' "$(dirname "$0")/../Dockerfile" |
			 sed 's/.*DEBIAN_TAG=\(.*\)-.*/\1/')
	DEBIAN_TAG=$(podman image search --list-tags debian --limit 1000000000 | \
		     grep "$DEBIAN_RELEASE-.*-slim" | sort -r | head -1 | sed 's/.*[ ]\+//')
fi

if [ "$CLEAN" = y ]; then
	for TARGET in $TARGETS; do
		docker rmi "ghcr.io/siemens/kas/$TARGET:$TAG" 2>/dev/null
	done
fi

if ! docker buildx inspect | grep -q "Driver Options:.*$BUILDKIT"; then
	BUILDX_INSTANCE=$(docker buildx create --driver-opt image="$BUILDKIT")
	docker buildx use "$BUILDX_INSTANCE"
fi

KAS_CLONE=$(mktemp -d --tmpdir kas-tmp.XXXXXXXXXX)
git clone . "$KAS_CLONE"
cd "$KAS_CLONE" || exit 1
git checkout -q "$GIT_REFSPEC"

RESULT=0
for TARGET in $TARGETS; do
	if ! build_image "$TARGET"; then
		RESULT=1
		break
	fi
done

cd - >/dev/null || exit 1
rm -rf "$KAS_CLONE"

exit $RESULT
