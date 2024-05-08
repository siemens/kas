.. _checkout-creds-label:

Credential Handling
===================

kas provides various mechanisms to inject credentials into the build.
By using :ref:`env-vars-label`, a fine grained control is possible. All
credentials are made available both to KAS, as well as inside the build
environment. However, not all mechanisms are natively supported by all tools.
As kas might need to modify credentials and config files, these are copied
into the isolated environment first. One exception is the SSH folder, where
changes are only performed if not yet present on the host.

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
url rewrites of git repositories (``insteadof``). To support the patching
of git repositories, kas injects a ``[user]`` section, possibly overwriting
an existing one. In addition, credential helpers can be used by
setting the corresponding environment variables. These are added to the
``.gitconfig`` file as well.

When running in a GitHub Action or GitLab CI job, the ``.gitconfig`` file
is automatically injected.

Github Actions
~~~~~~~~~~~~~~

In combination with the
`webfactory/ssh-agent <https://github.com/webfactory/ssh-agent>`_ action,
this automatically makes the required credentials available to kas and
bitbake.

Gitlab CI
~~~~~~~~~

When running in the GitLab CI, the ``CI_JOB_TOKEN`` can be used to access
git repositories via https. kas automatically adds this token to the
``.netrc`` file, where it is picked up by git. To be able to clone via ssh
locally, but via https in the CI, a rewrite rule needs to be added to the
``KAS_PREMIRRORS`` CI environment variable. Example:

.. code-block:: yaml

  variables:
    KAS_PREMIRRORS: "git@${CI_SERVER_HOST}: https://${CI_SERVER_HOST}/"

Netrc File
----------

A ``.netrc`` file can be used to provide credentials for git or the
HTTP(S) / FTP fetcher. When running in the Gitlab CI, the ``CI_JOB_TOKEN``
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
