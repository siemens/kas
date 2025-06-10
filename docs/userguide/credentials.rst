.. _checkout-creds-label:

Credential Handling
===================

kas provides various mechanisms to inject credentials into the build.
By using :ref:`env-vars-label`, a fine grained control is possible. All
credentials are made available both to KAS, as well as inside the build
environment. However, not all mechanisms are natively supported by all tools.
As kas might need to modify credentials and config files, these are copied
into the isolated environment first.

.. note::
  In general, file based credentials (e.g. ``.netrc``) are only copied
  if explicitly requested by setting the corresponding environment variable.
  Environment variable based credentials are automatically forwarded.

.. only:: man

  For details about credential related environment variables,
  see :manpage:`kas(1)`.

AWS Configuration
-----------------

For AWS, both conventional AWS config files as well as the environment
variable controlled OAuth 2.0 workflow are supported. Note, that KAS
internally rewrites the ``AWS_*`` environment variables into a AWS
config file to also support older versions of bitbake.

Git Configuration
-----------------

A ``.gitconfig`` file can be used to provide credentials as well as
URL rewrites of git repositories (``insteadof``). In addition, credential
helpers can be used by setting the corresponding environment variables.
These are added to the ``.gitconfig`` file as well. To support the patching
of git repositories, kas injects a ``[user]`` section, possibly overwriting
an existing one. After patching, the original user is restored (if set).

When running in a GitHub Action or GitLab CI job, the ``.gitconfig`` file
is automatically injected. Otherwise, the environment variable
``GITCONFIG_FILE`` needs to point to the `.gitconfig` kas should use.

GitHub Actions
~~~~~~~~~~~~~~

In combination with the
`webfactory/ssh-agent <https://github.com/webfactory/ssh-agent>`_ action,
this automatically makes the required credentials available to kas and
bitbake.

GitLab CI
~~~~~~~~~

When running in the GitLab CI, the ``CI_JOB_TOKEN`` can be used to access
git repositories via https. If ``CI_SERVER_HOST`` is also set,
kas automatically adds this token to the ``.netrc`` file,
where it is picked up by git. Further, kas configures git
to automatically rewrite the URLs of the repositories to clone via https
for repos stored on the same server. Technically this is achieved by adding
`insteadof` entries to the ``.gitconfig`` file.

For backwards compatibility, the git rewrite rules are only added if
``.gitconfig`` does not exist and no SSH configuration is provided (either
via the kas ``SSH_`` variables or using ``.ssh/config``).

If the ``CI_REGISTRY``, ``CI_REGISTRY_USER`` and ``CI_JOB_TOKEN`` variables
are set, kas automatically creates a login file for the container
registry at ``~/.docker/config.json``. This file is compatible with
docker, podman and even skopeo.

.. note::
  Make sure to assign the correct permissions to the ``CI_JOB_TOKEN``.
  For details, see `GitLab CI/CD job token <https://docs.gitlab.com/ee/ci/jobs/ci_job_token.html>`_.

Container Registry Authentication File
--------------------------------------

A file named ``config.json`` is saved as ``.docker/config.json`` in the kas
home directory. It contains credentials for the container registry login.
The syntax is described in the `containers-auth.json specification <https://github.com/containers/image/blob/main/docs/containers-auth.json.5.md>`_.
The authentication file is compatible with docker, podman and skopeo.
When running in the GitLab CI, the ``CI_JOB_TOKEN`` is appended to
automatically grant access according to the job permissions.

Netrc File
----------

A ``.netrc`` file can be used to provide credentials for git or the
HTTP(S) / FTP fetcher. When running in the GitLab CI, the ``CI_JOB_TOKEN``
is appended to automatically grant access to repositories that can be
accessed by the user that triggered the CI pipeline.

SSH
---

The ssh folder of the calling user is automatically shared with kas. This
is currently not controllable, as ssh does not obey the ``$HOME`` variable.
This can be used to inject both credentials, as well as ssh configuration
items into the kas environment.

.. note::
  Modifications to the ``.ssh/config`` file are only performed if the file
  is not present yet.

In addition, an external ssh-agent can be made available in the kas
environment by setting the ``SSH_AUTH_SOCK`` environment variable.
As an alternative, ssh private keys can be added to an internal ssh agent
by setting ``SSH_PRIVATE_KEY`` or ``SSH_PRIVATE_KEY_FILE``.

.. note::
  The use of an external ssh agent cannot be combined with options that
  require an internal ssh agent.
