Command line usage
==================

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas


Environment variables
---------------------

+--------------------------+--------------------------------------------------+
| Environment variables    | Description                                      |
+==========================+==================================================+
| ``KAS_WORK_DIR``         | The path of the kas work directory, current work |
|                          | directory is the default.                        |
+--------------------------+--------------------------------------------------+
| ``KAS_BUILD_DIR``        | The path build directory,                        |
|                          | ``${KAS_WORK_DIR}/build`` is the default.        |
+--------------------------+--------------------------------------------------+
| ``KAS_REPO_REF_DIR``     | The path to the repository reference directory.  |
|                          | Repositories in this directory are used as       |
|                          | references when cloning. In order for kas to     |
|                          | find those repositories, they have to be named   |
|                          | in a specific way. The repo URLs are translated  |
|                          | like this:                                       |
|                          | "https://github.com/siemens/meta-iot2000.git"    |
|                          | resolves to the name                             |
|                          | "github.com.siemens.meta-iot2000.git".           |
|                          | Repositories that are not found will be cloned   |
|                          | below this directory. Multiple instances of kas  |
|                          | can simultaneously work on the same directory,   |
|                          | as long as the underlying filesystem is POSIX    |
|                          | compatible.                                      |
+--------------------------+--------------------------------------------------+
| ``KAS_DISTRO``           | This overwrites the respective setting in the    |
| ``KAS_MACHINE``          | configuration file.                              |
| ``KAS_TARGET``           |                                                  |
| ``KAS_TASK``             |                                                  |
+--------------------------+--------------------------------------------------+
| ``KAS_PREMIRRORS``       | Specifies alternatives for repo URLs. Just like  |
| ``DISTRO_APT_PREMIRRORS``| bitbake ``PREMIRRORS``, this variable consists   |
|                          | of new-line separated entries. Each entry        |
|                          | defines a regular expression to match a URL and, |
|                          | space-separated, its replacement. E.g.:          |
|                          | "http://.*\.someurl\.io/ http://localmirror.net/"|
+--------------------------+--------------------------------------------------+
| ``SSH_PRIVATE_KEY``      | Variable containing the private key that should  |
|                          | be added to an internal ssh-agent. This key      |
|                          | cannot be password protected. This setting is    |
|                          | useful for CI build servers. On desktop          |
|                          | machines, an ssh-agent running outside the kas   |
|                          | environment is more useful.                      |
+--------------------------+--------------------------------------------------+
| ``SSH_PRIVATE_KEY_FILE`` | Path to the private key file that should be      |
|                          | added to an internal ssh-agent. This key cannot  |
|                          | be password protected. This setting is useful    |
|                          | for CI build servers. On desktop machines, an    |
|                          | ssh-agent running outside the kas environment is |
|                          | more useful.                                     |
+--------------------------+--------------------------------------------------+
| ``SSH_AUTH_SOCK``        | SSH authentication socket. Used for cloning over |
|                          | SSH (alternative to ``SSH_PRIVATE_KEY`` or       |
|                          | ``SSH_PRIVATE_KEY_FILE``).                       |
+--------------------------+--------------------------------------------------+
| ``DL_DIR``               | Environment variables that are transferred to    |
| ``SSTATE_DIR``           | the bitbake environment.                         |
| ``TMPDIR``               |                                                  |
+--------------------------+--------------------------------------------------+
| ``http_proxy``           | These variables define the proxy configuration   |
| ``https_proxy``          | bitbake should use.                              |
| ``ftp_proxy``            |                                                  |
| ``no_proxy``             |                                                  |
+--------------------------+--------------------------------------------------+
| ``GIT_PROXY_COMMAND``    | Set proxy for native git fetches. ``NO_PROXY``   |
| ``NO_PROXY``             | is evaluated by OpenEmbedded's oe-git-proxy      |
|                          | script.                                          |
+--------------------------+--------------------------------------------------+
| ``SHELL``                | The shell to start when using the `shell`        |
|                          | plugin.                                          |
+--------------------------+--------------------------------------------------+
| ``TERM``                 | The terminal options used in the `shell` plugin. |
+--------------------------+--------------------------------------------------+
| ``AWS_CONFIG_FILE``      | Path to the awscli configuration and credentials |
| |aws_cred|               | file that are copied to the kas home dir.        |
+--------------------------+--------------------------------------------------+
| |git_cred|               | Allows to set and configure the git credential   |
|                          | helper in the `.gitconfig` of the kas user.      |
+--------------------------+--------------------------------------------------+
| ``NETRC_FILE``           | Path to a .netrc file which will be copied to    |
|                          | the kas home dir as .netrc.                      |
+--------------------------+--------------------------------------------------+
| ``CI_SERVER_HOST``       | Environment variables from gitlab CI, if set     |
| ``CI_JOB_TOKEN``         | .netrc is configured to allow fetching from      |
|                          | the gitlab instance. An entry will be appended   |
|                          | in case ``NETRC_FILE`` was given as well. Note   |
|                          | that if the file already contains an entry for   |
|                          | that host most tools would probably take that    |
|                          | first one.                                       |
+--------------------------+--------------------------------------------------+
| ``BB_NUMBER_THREADS``    | Environment variables to control the concurrency |
| ``PARALLEL_MAKE``        |                                                  |
+--------------------------+--------------------------------------------------+

.. |aws_cred| replace:: ``AWS_SHARED_CREDENTIALS_FILE``
.. |git_cred| replace:: ``GIT_CREDENTIAL_HELPER`` ``GIT_CREDENTIAL_USEHTTPPATH``
