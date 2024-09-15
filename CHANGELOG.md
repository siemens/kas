4.5
- kas: avoid bitbake parsing due to non-deterministic layer patches
- kas: correctly handle upstream ff merges on fetch
- kas: keep git committer identity if provided in .gitconfig
- kas: add support for container registry authentication
- kas: Improve GitLab CI rewrite rules for git
- kas-container: Use official snapshot.debian.org
- kas-container: Fix positional argument processing with for-all-repos
- kas-container: allow recent Ubuntu builds via isar
- kas-container: re-add deterministic metadata
- docs: document difference between file and env credentials
- sign pip packages on release

4.4
- kas: Auto-import runner-provided .gitconfig also inside GitLab-CI
- kas: Auto-inject git credentials on gitlab ci
- kas: Add --keep-config-unchanged to preserve repos and configs on actions
- kas: Fix --skip'ing multiple steps
- kas: List --skip'able steps in --help
- kas: Add support for shallow clones
- kas: Add support to create provenance build attestations
- kas: Add config key to describe build artifacts (used by attestation)
- kas: Add option to dump-plugin to include VCS info of local repos
- kas-container: Handle missing extra argument in subcommands gracefully
- kas-container: improve container reproduction using git commit date
- docs: Several format improvements
- docs: Add simple examples

4.3.2
- kas: don't add comments to .netrc, fixing gitlab-ci
- kas: make file permissions on credentials more strict (not a security fix)
- kas: align hg semantics of repo dirty checking
- kas-container: fix warnings from shellcheck 0.9.0
- docs: do not build docs against installed version
- docs: update to match bitbake variable changes
- docs: unify spelling of kas
- docs: document scope of environment variables

4.3.1
- kas: Fix regression of 4.3 when using SSH_PRIVATE_KEY[_FILE]
- kas-container: Update to debian:bookworm-20240311-slim (implicitly)

4.3
- kas: fix including from transitively referenced repos
- kas: Add support for .gitconfig pass-through
- kas: Optimize checkout of repos in larger configurations
- kas: Reduce verbosity of kas startup output
- kas: check if branch contains commit if both are set
- kas: Improve error reporting in several places
- kas-container: Bit-identically reproducible images
- kas-container: Enrich manifests with provenance information
- kas-container: Add bash completion for kas
- docs: Separate man pages per subcommand
- docs: Various smaller improvements

4.2
- kas: Fix lock files when references repos by tags
- kas: add forgotten `tag` key to repos `defaults`
- kas: add support for OAuth2 worflow
- kas-container: add python3-websockets
- kas-container: unify error handling

4.1
- kas: Add "tag" property to repo, to replace usage of refspec
- kas: generalize revision locking to all included files
- kas: allow for --skip repos_checkout
- kas: forward SSTATE_MIRRORS environment variable
- kas: Allow PyYAML 6, fixing dependency conflicts
- kas: Add Python 3.12 support
- kas: Update jsonschema upper version limit
- kas: menu plugin: Reorder help and exit buttons
- kas: menu plugin: Add separate return button for submenus
- kas: Fix Mercurial's branch resolution
- kas-container: detect build system on clean commands
- kas-container: report error if ssh-agent is requested but not running

4.0
- kas container: Switch to Debian bookworm
- kas-container: Make kas-isar ready for mmdebstrap

3.3
- kas: Introduce commit and branch as alternative to refspec key
- kas: Warn if a repo uses legacy refspec
- kas: add support for lock files via dump plugin
- kas: track root repo dir config files of menu plugin
- kas: add support for --log-level argument
- kas: add GIT_CREDENTIAL_USEHTTPPATH environment variable
- kas: improve error reporting
- kas: drop support for Python 3.5
- kas-container: fix invocations with --isar for some layers
- kas-container: Purge tmp* on clean
- kas-container: enable colored logging

3.2.3
- kas-container: mount KAS_REPO_REF_DIR rw to support auto-creation
- kas-container: fix --ssh-dir (3.2.2 regression)
- container: Use original UID/GID when run without kas-container (3.2.2 regression)

3.2.2
- kas-container: Start as non-root when running without kas-container
- kas-container: Disable git safe.directory when running without kas-container
- kas-container: Make sure privileged podman will find sbin tools
- docs: Leave notice on inherit integrity weaknesses of repo fetches
- docs: Add a SECURITY.md

3.2.1
- kas-container: Add unzip package to kas-base
- docs: Fix description of container image generation
- docs: Fix description of bblayers_conf_header and local_conf_header

3.2
- kas: add conditional, default-free environment variables
- kas: add plugin to dump flattened config and resolve repo refs
- kas: auto-create repo refs when KAS_REPO_REF_DIR is set
- kas: print build bitbake command when running shell
- kas: forward BB_NUMBER_THREADS and PARALLEL_MAKE env vars into build
- kas-container: Fix engine detection when docker is an alias for podman
- kas-container: forward DISTRO_APT_PREMIRRORS environment variable
- kas-container: reduce log chattiness of container runtime
- kas-container: write debug messages to stderr
- kas-container: Refresh Yocto build dependency list
- kas-container: Rework generation of kas images, shrinking kas-isar
- kas-container: avoid deploying the python pip cache

3.1
- kas: Add support for authentication with gitlab CI
- kas: Add NETRC_FILE to allow passing credentials into kas home
- kas: for-all-repos: Add option to keep current env
- kas: Avoid whitespace warnings when applying repo patches
- kas: Use relative layer dirs to make build relocatable
- kas: Allow "deleting" url/path of repo in override
- kas: Fix repo-relative include file handling if no config file is given
- kas: Fix include errors from repos defined via multiple yaml files
- kas: Fix handling of -- separator in the absence of a config file
- kas: Bundle kas-container script
- kas-container: Add support for podman >= 4.1
- kas-container: Add '--ssh-agent' option
- kas-container: Add telnet to image
- kas-container: Remove obsolete schroot mntpoint
- kas-container: Reduce the image size a bit

3.0.2
- kas-container: Fix the fix for chatty sbuild-adduser in kas-isar

3.0.1
- kas-container: Silence chatty sbuild-adduser in kas-isar

3.0
- kas: git fetch always with quiet flag, suppressing false error messages
- kas: Add BB_ENV_PASSTHROUGH_ADDITIONS support
- kas: shell: Add option to keep current environment
- kas: Raise an error on missing repo refspec
- kas-container: Base containers on bullseye
- kas-container: Add pigz package to container to enable parallel compression
- kas-container: Support for sbuild in kas-isar
- kas-container: podman: Remove --pid=host
- kas-container: Start init service inside container
- kas-container: Add cleansstate and cleanall
- kas-container: Pass http_proxy et.al through sudo
- kas-container: Address shellcheck findings in container-entrypoint
- docs: Add recommendation for repo-id naming
- docs: Clarify local file include paths

2.6.3
- kas: Do not overwrite existing .ssh/config
- kas: Properly describe package build
- kas-container: create KAS_WORK_DIR if it not exists
- kas-container: validate KAS_REPO_REF_DIR correctness
- docs: Fix generation
- docs: Extended "layers" section in the user guide.

2.6.2
- kas-container: Restore oe-git-proxy location (/usr/bin)
- kas-container: Drop world-write permission from /kas folder

2.6.1
- kas: fix installation via pip

2.6
- kas: Add kconfiglib-based menu plugin
- kas: Enable kas to checkout repositories using git credentials
- kas: Enable gerrit/gitlab/github refspecs
- kas: Write more bblayers.conf boilerplate settings
- kas: Add environment variable SSH_PRIVATE_KEY_FILE
- kas: Add support for relative KAS_WORK/BUILD/REPO_REF_DIR paths
- kas: Move config json schema to standalone json file
- kas: Avoid duplicate cloning of repos in command line includes
- kas: for_all_repos: Exit on command failure
- kas: for_all_repos: Fix KAS_REPO_URL or unversioned repos
- kas: Declare proxy_config obsolete
- kas-container: install lz4
- kas-container: install g++-multilib
- kas-container: install newer git-lfs
- kas-container: Enter with /repo as current dir
- kas-container: Carry oe-git-proxy locally and relocate to /usr/local/bin

2.5
- kas: Apply patches before doing an environment setup
- kas: repos: strip dot from layer name
- kas: Introduce KAS_BUILD_DIR environment variable
- kas: add GIT_CREDENTIAL_HELPER environment variable
- kas-container: add `--git-credential-store` options
- kas-container: mount /repo as read-write for shell command
- kas-container: add an argument to get version information
- kas-container: Add support for checkout and for-all-repos
- kas-container: add support to set a custom container images location
- kas-container: Fix mounting of custom KAS_REPO_REF_DIR
- kas-container: Add skopeo and umoci to ISAR image
- kas-container: add sudo to standard kas image

2.4
- kas: Silence "Exception ignored when trying to write to the signal wakeup fd"
- kas: drop bitbakes "-k" from the default args
- kas: fix repos path if no url, but path given
- kas: Set upper version limit for dependencies
- kas-container: Add support for rootless podman with userns keep-id
- kas-container: Add support for multi-word --command arguments
- kas-container: make sure that we pass shellcheck
- kas-container/kas*: Add support for multi-arch containers
- kas-container/kas: Pull all Python dependencies from Debian
- kas-container/kas-isar: Drop grub package

2.3.3
- Fix binfmt setup in kas-isar container image

2.3.2
- Fix release script fix /wrt kas-container image version updates

2.3.1
- Fix release scripting

2.3
- kas: add "checkout" and for-all-repos subcommands
- kas: add python 3.9 compatibility
- kas: improve documentation
- config: add build_system property to pre-select OE/Yocto or Isar
- kas-container: rename from kas-docker
- kas-container: add support for build_system property (making --isar optional)
- kas-container: adjust environment variables interface
- kas-container: switch to github container repository
- kas-container: add support for Debian bullseye cross building
- kas-container: add zstd package

2.2
- kas: allow extra bitbake arguments to be passed
- kas: add --force-checkout and --update arguments to ease CI usage
- kas: allow for layer-free repositories
- kas: fix cloning of repos without default branch
- kas: enable standard-conforming .yaml file extensions
- kas-docker: enhance with podman support
- kas-docker: switch to /bin/bash as SHELL per default
- config: Allow a default refspec to be specified
- config: Allow a default repo to be specified for patches

2.1.1
- repos: Silence pycodestyle error (that broke docker image generation)

2.1
- Add support for S3 fetcher to docker image
- Lift Python minimal requirements to 3.5
- Fix reporting of of repo patch IDs
- config: use 'qemux86-64' instead of 'qemu' as default for KAS_MACHINE
- Ensure SSH key ends with newline
- kas-docker: Make it harder to run as root
- kas-docker: Make loop device passing optional
- kas-docker: Various fixes

2.0
- Add support for Yocto 3.0 / latest Isar
- Move docker image to Debian buster
- Add git-lfs support to docker image
- Add Yocto testimage dependencies to docker image

1.1
- Restore mercurial support
- Add -c and --cmd as aliases for --task
- Fix repo patching when using a branch name as refspec
- Update repo remote URL on kas file changes
- kas-docker: fix SHELL forwarding
- kas-docker: use released image, rather than "latest"
- kas-docker: allow to define custom image version
- kasproject/kas: enable devshell and menuconfig targets
- kasproject/kas image: add gnupg and quilt
- kasproject/kas-isar image: fix /var/tmp handling

1.0
- isar: Take qemu-user-static from buster and adjust binfmt setup

0.20.1
- kas-docker: Restore KAS_PREMIRRORS support

0.20.0
- kas-docker: enable passing SSH configs
- kas-docker: add --no-proxy-from-env option
- kas-docker: Pass in NO_PROXY
- Add KAS_PREMIRRORS support
- Remove SSH_AGENT_PID forwarding

0.19.0
- Recursive include handler refactoring and cleanups
- A lot of code cleanups, refactoring and bug fixings
- Isar docker support improvements

0.18.0
- Add patch support for repos
- Use git diff-index to check if repo is dirty
- docker: add debootstrap and qemu-user-static

0.17.0
- Add iproute and zx-utils to the docker image
- Fix relative path for repos
- Write MACHINE and DISTRO as weak defaults

0.16.0
- Support Mercurial repos
- Support Gentoo distro

0.15.0
- Environment variable passthrough
- Support major distro variants
- Add initial support for multiconfig

0.14.0
- Multi-target support
- Avoid downloading same repo twice

0.13.0
- Increase config file version

0.12.0
- Remove dynamic configuration support (Python config files)
- Shell command prepares complete bitbake configuration
- Add to define task in config and environment
- Improved error handling and reporting

0.11.0
- Allow in-tree repos not to be in a git repo
- Pass through git proxy related environment variables
- Write deterministic local.conf and bblayers.con
- Make configuration file versioning independent of project version
- Cleanups for uploading project to PyPI
- Print proper error message for config file format exception

0.10.0
- Docker image creation (Debian Stretch), pushed on kasproject/kas
- Restructure documentation add support for Sphinx export it to readthedocs
- Add support for include feature for Yaml files
- Add support for Isar build system
- Handling of SIGTERM/TERM improved
- Parallel download of git sources
- Allow environment to overwrite proxy, target, machine and distro
- Add unit testing for include/merge config file handling
- Rename sublayers back to layers
- pylint & pep8 cleanups
- Allow to define workdir via KAS_WORK_DIR
- Shell honors SHELL and TERM environment variable

0.9.0
- initial public release
