#!/bin/bash

usage() {
	echo "$0 [repo-path]"
	exit 1
}

if [ $# -gt 1 ] || [ "$1" == "--help" ]; then
	usage
fi

repo=${1:-.}

# find out if current dir is under a git repo
commit=$(git -C ${repo} rev-parse HEAD 2>/dev/null)
if [ -n "$commit" ]; then
	repo_root=$(git -C ${repo} rev-parse --show-toplevel)
	list_cmd="git -C ${repo_root} ls-tree -r --name-only HEAD"
else
	# not git, check if we are in an hg repo
	commit=$(hg -R "${repo}" id -i)
	if [ -z "$commit" ]; then
		echo "Neither a git nor a hg repo"
		exit 1
	fi
	repo_root=$(hg -R ${repo} root)
	list_cmd="hg -R ${repo_root} manifest"
fi

# Obtain the full file list of the repo, dump header and content of each.
# That list is newline-separated in the output of $list_cmd.
# It is then sorted in traditional order (LC_ALL=C) to ensure a stable output.
IFS=$'\n'
for file in $(eval ${list_cmd} | LC_ALL=C sort); do

	# print header line: file-name raw-mode file-size\n
	printf "%s %d %o\n" "${file}" \
		$(stat -c %s "${repo_root}/${file}") \
		0x$(stat -c %f "${repo_root}/${file}")

	# print file, either the link or the content of a regular file
	readlink -n "${repo_root}/${file}" || cat "${repo_root}/${file}"

done | sha256sum | sed 's/-/'"${commit}"'/'
# The hash was taken over all of this and printed in sha256sum format, just
# replacing the stdin mark '-' with the actual commit ID.
