kas uses a number of environment variables to configure its behavior.
The `Variables Glossary`_ provides an overview, wherein the tuple (C,K,E)
denotes the scope of the variable.

All directories that are passed to kas by setting the corresponding
environment variables (e.g. ``KAS_WORK_DIR``, ``KAS_BUILD_DIR``, ...) must
not overlap with each other, except for overlapping with ``KAS_WORK_DIR``
(i.e. the build|sstate|downloads|repo-ref dirs can be below the work dir).
Environment variables that reference a file or directory must have a valid
path that is accessible and readable.

Variable Scope
~~~~~~~~~~~~~~

**kas-container (C)**

The variable is processed or forwarded by the ``kas-container`` script.
For some variables, the variable is re-written to the container's
directory layout.

.. note::
    The ``env`` section of the `project configuration` can be used to make
    arbitrary environment variables available to the build environment. When
    invoking the build via ``kas-container``, make sure to also forward the
    corresponding environment variables into the container.

**kas (K)**

The variable is processed by kas itself. Some variables (e.g. the credentials
for the awscli) are re-written to configuration files to also support older
versions of the tooling.

**build environment (E)**

The variable is exported into the build environment. In this environment, the
``bitbake`` command is executed.

**config-file (c)**

The variable can be set in the ``env`` section of the
:ref:`project-configuration-label`. Note, that a value provided by the calling
environment takes precedence over the value in the configuration file.

Variables Glossary
~~~~~~~~~~~~~~~~~~

These environment variables are processed before the configuration file is
read (except if stated otherwise). By that, they cannot be defined or
overwritten using the ``env`` section of the config file.

+--------------------------+--------------------------------------------------+
| Environment variables    | Description                                      |
+==========================+==================================================+
| ``KAS_WORK_DIR``         | The path of the kas work directory, current work |
| (C, K)                   | directory is the default. This directory must    |
|                          | exist if set.                                    |
+--------------------------+--------------------------------------------------+
| ``KAS_BUILD_DIR``        | The path of the build directory,                 |
| (C, K)                   | ``${KAS_WORK_DIR}/build`` is the default.        |
|                          | The parent directory must exist if set.          |
+--------------------------+--------------------------------------------------+
| ``KAS_REPO_REF_DIR``     | The path to the repository reference directory.  |
| (C, K)                   | Repositories in this directory are used as       |
|                          | references when cloning. In order for kas to     |
|                          | find those repositories, they have to be named   |
|                          | in a specific way. The repo URLs are translated  |
|                          | like this:                                       |
|                          | ``https://github.com/siemens/meta-iot2000.git``  |
|                          | resolves to the name                             |
|                          | ``github.com.siemens.meta-iot2000.git``.         |
|                          | Repositories that are not found will be cloned   |
|                          | below this directory. Multiple instances of kas  |
|                          | can simultaneously work on the same directory,   |
|                          | as long as the underlying filesystem is POSIX    |
|                          | compatible. This directory must exist if set.    |
+--------------------------+--------------------------------------------------+
| ``KAS_DISTRO``           | This overwrites the respective setting in the    |
| ``KAS_MACHINE``          | configuration file.                              |
| ``KAS_TARGET``           |                                                  |
| ``KAS_TASK``             |                                                  |
| (C, K)                   |                                                  |
+--------------------------+--------------------------------------------------+
| ``KAS_PREMIRRORS``       | Specifies alternatives for repo URLs. Just like  |
| (C, K)                   | bitbake ``PREMIRRORS``, this variable consists   |
|                          | of new-line separated entries. Each entry        |
|                          | defines a regular expression to match a URL and, |
|                          | space-separated, its replacement. E.g.:          |
|                          | ``http://.*\.someurl\.io/                        |
|                          | http://localmirror.net/``                        |
+--------------------------+--------------------------------------------------+
| ``DISTRO_APT_PREMIRRORS``| Specifies alternatives for apt URLs. Just like   |
| (C,c)                    | ``KAS_PREMIRRORS``.                              |
+--------------------------+--------------------------------------------------+
| ``KAS_CLONE_DEPTH``      | Perform shallow git clone/fetch using --depth=N  |
| (C, K)                   | specified by this variable. This is useful in    |
|                          | case CI always starts with empty work directory  |
|                          | and this directory is always discarded after the |
|                          | CI run.                                          |
+--------------------------+--------------------------------------------------+
| ``SSH_PRIVATE_KEY``      | Variable containing the private key that should  |
| (K)                      | be added to an internal ssh-agent. This key      |
|                          | cannot be password protected. This setting is    |
|                          | useful for CI build servers. On desktop          |
|                          | machines, an ssh-agent running outside the kas   |
|                          | environment is more useful.                      |
+--------------------------+--------------------------------------------------+
| ``SSH_PRIVATE_KEY_FILE`` | Path to the private key file that should be      |
| (K)                      | added to an internal ssh-agent. This key cannot  |
|                          | be password protected. This setting is useful    |
|                          | for CI build servers. On desktop machines, an    |
|                          | ssh-agent running outside the kas environment is |
|                          | more useful.                                     |
+--------------------------+--------------------------------------------------+
| ``SSH_AUTH_SOCK``        | SSH authentication socket. Used for cloning over |
| (C,K,E)                  | SSH (alternative to ``SSH_PRIVATE_KEY`` or       |
|                          | ``SSH_PRIVATE_KEY_FILE``).                       |
+--------------------------+--------------------------------------------------+
| ``DL_DIR``               | Environment variables that are transferred to    |
| ``SSTATE_DIR``           | the bitbake environment. The ``DL_DIR`` and      |
| ``SSTATE_MIRRORS``       | ``SSTATE_DIR`` directories are created along     |
| (C,K,E,c)                | with their parents, if set.                      |
+--------------------------+--------------------------------------------------+
| ``TMPDIR`` (K,E,c)       | Directory for temporary files.                   |
+--------------------------+--------------------------------------------------+
| ``http_proxy``           | These variables define the proxy configuration   |
| ``https_proxy``          | bitbake should use.                              |
| ``ftp_proxy``            |                                                  |
| ``no_proxy``             |                                                  |
| (C,K,E)                  |                                                  |
+--------------------------+--------------------------------------------------+
| ``GIT_PROXY_COMMAND`` (E)| Set proxy for native git fetches. ``NO_PROXY``   |
| ``NO_PROXY`` (C,K,E)     | is evaluated by OpenEmbedded's oe-git-proxy      |
|                          | script.                                          |
+--------------------------+--------------------------------------------------+
| ``SHELL``                | The shell to start when using the ``shell``      |
| (C,K,E)                  | plugin and in the bitbake environment.           |
+--------------------------+--------------------------------------------------+
| ``TERM``                 | The terminal options used in the ``shell``       |
| (C,K,E)                  | plugin and in the bitbake environment.           |
+--------------------------+--------------------------------------------------+
| ``TZ`` (C)               | Timezone settings.                               |
+--------------------------+--------------------------------------------------+
| ``AWS_CONFIG_FILE``      | Path to the awscli configuration and credentials |
| |aws_cred|               | files that are copied to the kas home dir.       |
| (K,C)                    |                                                  |
+--------------------------+--------------------------------------------------+
| |git_cred|               | Allows one to set and configure the git          |
| (K,C)                    | credential helper in the `.gitconfig` of the kas |
|                          | user.                                            |
+--------------------------+--------------------------------------------------+
| ``GITCONFIG_FILE``       | Path to a `.gitconfig` file which will be        |
| (K,C)                    | copied to the kas home dir as `.gitconfig`.      |
+--------------------------+--------------------------------------------------+
| ``NETRC_FILE``           | Path to a .netrc file which will be copied to    |
| (K,C)                    | the kas home dir as .netrc.                      |
+--------------------------+--------------------------------------------------+
| ``NPMRC_FILE``           | Path to a .npmrc file which will be copied to    |
| (K,C)                    | the kas home dir as .npmrc.                      |
+--------------------------+--------------------------------------------------+
| ``REGISTRY_AUTH_FILE``   | Path to a container registry authentication file.|
| (K,C)                    |                                                  |
+--------------------------+--------------------------------------------------+
| |ci_server_vars|         | Environment variables from GitLab CI, if set     |
| ``CI_JOB_TOKEN``         | .netrc is configured to allow fetching from      |
| ``CI_JOB_URL``           | the GitLab instance. An entry will be appended   |
| ``CI_REGISTRY``          | in case ``NETRC_FILE`` was given as well. Note   |
| ``CI_REGISTRY_USER``     | that if the file already contains an entry for   |
| (K)                      | that host most tools would probably take that    |
|                          | first one. The job URL is added to the           |
|                          | provenance attestation (if enabled).             |
|                          | If ``CI_REGISTRY`` and ``CI_REGISTRY_USER`` is   |
|                          | also set, a container registry login file is     |
|                          | created, which is used by docker, podman and     |
|                          | skopeo. In case ``REGISTRY_AUTH_FILE`` was given |
|                          | as well, the CI login data will be appended to   |
|                          | that file.                                       |
|                          | The required base64 encoded login data is        |
|                          | generated by kas.                                |
+--------------------------+--------------------------------------------------+
| ``GITHUB_ACTIONS``       | Environment variables from GitHub actions or     |
| ``GITLAB_CI``            | GitLab CI. If set to `true`, `.gitconfig` is     |
| (K)                      | automatically imported.                          |
|                          | For details, see ``GITCONFIG_FILE``.             |
+--------------------------+--------------------------------------------------+
| ``REMOTE_CONTAINERS`` (K)| Environment variables related to VSCode Remote   |
| ``REMOTE_CONTAINERS_<x>``| Containers. If running in this environment,      |
| (K,E)                    | `.gitconfig` is automatically imported.          |
+--------------------------+--------------------------------------------------+
| ``BB_NUMBER_THREADS``    | Environment variables to control the concurrency.|
| ``PARALLEL_MAKE``        |                                                  |
| (C,K,E)                  |                                                  |
+--------------------------+--------------------------------------------------+
| ``KAS_IMAGE_VERSION`` (C)| Select the version of the (official) kas         |
|                          | container (e.g. 4.5).                            |
+--------------------------+--------------------------------------------------+
| ``KAS_CONTAINER_IMAGE``  | Select the container image (full OCI path        |
| (C)                      | including tag).                                  |
+--------------------------+--------------------------------------------------+
| ``KAS_CONTAINER_ENGINE`` | Explicitly set the container engine (either      |
| (C)                      | ``docker`` or ``podman``). If not set, this is   |
|                          | auto-detected (preference: docker).              |
+--------------------------+--------------------------------------------------+

.. |aws_cred| replace:: ``AWS_ROLE_ARN``
                        ``AWS_SHARED_CREDENTIALS_FILE``
                        ``AWS_WEB_IDENTITY_TOKEN_FILE``
.. |git_cred| replace:: ``GIT_CREDENTIAL_HELPER`` ``GIT_CREDENTIAL_USEHTTPPATH``
.. |ci_server_vars| replace:: ``CI_SERVER_HOST``
                              ``CI_SERVER_PORT``
                              ``CI_SERVER_PROTOCOL``
                              ``CI_SERVER_SHELL_SSH_HOST``
                              ``CI_SERVER_SHELL_SSH_PORT``

.. only:: html

    For details about the access of remote resources, see
    :ref:`checkout-creds-label`.
