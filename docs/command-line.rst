Command line usage
==================

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas


Environment variables
---------------------

+-----------------------+-----------------------------------------------------+
| Environment variables | Description                                         |
+=======================+=====================================================+
| ``KAS_WORK_DIR``      | The path of the kas work directory, current work    |
|                       | directory is the default.                           |
| ``KAS_BUILD_DIR``     | The path build directory, ``${KAS_WORK_DIR}/build`` |
|                       | is the default.                                     |
+-----------------------+-----------------------------------------------------+
| ``KAS_REPO_REF_DIR``  | The path to the repository reference directory.     |
|                       | Repositories in this directory are used as          |
|                       | references when cloning. In order for kas to find   |
|                       | those repositories, they have to be named in a      |
|                       | specific way. The repo URLs are translated like     |
|                       | this: "https://github.com/siemens/meta-iot2000.git" |
|                       | resolves to the name                                |
|                       | "github.com.siemens.meta-iot2000.git".              |
+-----------------------+-----------------------------------------------------+
| ``KAS_DISTRO``        | This overwrites the respective setting in the       |
| ``KAS_MACHINE``       | configuration file.                                 |
| ``KAS_TARGET``        |                                                     |
| ``KAS_TASK``          |                                                     |
+-----------------------+-----------------------------------------------------+
| ``KAS_PREMIRRORS``    | Specifies alternatives for repo URLs. Just like     |
|                       | bitbake ``PREMIRRORS``, this variable consists of   |
|                       | new-line separated entries. Each entry defines a    |
|                       | regular expression to match a URL and, space-       |
|                       | separated, its replacement. E.g.:                   |
|                       | "https://.*\.somehost\.io/ https://localmirror.net/"|
+-----------------------+-----------------------------------------------------+
| ``SSH_PRIVATE_KEY``   | Path to the private key file that should be added   |
|                       | to an internal ssh-agent. This key cannot be        |
|                       | password protected. This setting is useful for CI   |
|                       | build servers. On desktop machines, an ssh-agent    |
|                       | running outside the kas environment is more useful. |
+-----------------------+-----------------------------------------------------+
| ``SSH_AUTH_SOCK``     | SSH authentication socket. Used for cloning over    |
|                       | SSH (alternative to ``SSH_PRIVATE_KEY``).           |
+-----------------------+-----------------------------------------------------+
| ``DL_DIR``            | Environment variables that are transferred to the   |
| ``SSTATE_DIR``        | bitbake environment.                                |
| ``TMPDIR``            |                                                     |
+-----------------------+-----------------------------------------------------+
| ``http_proxy``        | This overwrites the proxy configuration in the      |
| ``https_proxy``       | configuration file.                                 |
| ``ftp_proxy``         |                                                     |
| ``no_proxy``          |                                                     |
+-----------------------+-----------------------------------------------------+
| ``GIT_PROXY_COMMAND`` | Set proxy for native git fetches. ``NO_PROXY`` is   |
| ``NO_PROXY``          | evaluated by OpenEmbedded's oe-git-proxy script.    |
+-----------------------+-----------------------------------------------------+
| ``SHELL``             | The shell to start when using the `shell` plugin.   |
+-----------------------+-----------------------------------------------------+
| ``TERM``              | The terminal options used in the `shell` plugin.    |
+-----------------------+-----------------------------------------------------+
| ``AWS_CONFIG_FILE``   | Path to the awscli configuration and credentials    |
| |aws_cred|            | file that are copied to the kas home dir.           |
+-----------------------+-----------------------------------------------------+

.. |aws_cred| replace:: ``AWS_SHARED_CREDENTIALS_FILE``
