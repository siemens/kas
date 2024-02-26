User Guide
==========

Dependencies & installation
---------------------------

This project depends on

- Python 3
- distro Python 3 package
- jsonschema Python 3 package
- PyYAML Python 3 package
- GitPython Python 3 package
- kconfiglib Python 3 package (optional, for menu plugin)
- NEWT Python 3 distro package (optional, for menu plugin)

To install kas into your python site-package repository, run::

    $ sudo pip3 install .


Usage
-----

There are (at least) four options for using kas:

- Install it locally via pip to get the ``kas`` command.
- Use the container image locally. In this case, download the ``kas-container``
  script from the kas repository and use it in place of the ``kas`` command.
  The script version corresponds to the kas tool and the kas image version.
- Use the container image in CI. Specify
  ``ghcr.io/siemens/kas/kas[-isar][:<x.y>]`` in your CI script that requests
  a container image as runtime environment. See
  https://github.com/orgs/siemens/packages/container/kas%2Fkas/versions and
  https://github.com/orgs/siemens/packages/container/kas%2Fkas-isar/versions for
  all available images.
- Use the **run-kas** wrapper from this directory. In this case,
  replace ``kas`` in the examples below with ``path/to/run-kas``.

Start build::

    $ kas build /path/to/kas-project.yml

Alternatively, experienced bitbake users can invoke usual **bitbake** steps
manually, e.g.::

    $ kas shell /path/to/kas-project.yml -c 'bitbake dosfsutils-native'

kas will place downloads and build artifacts under the current directory when
being invoked. You can specify a different location via the environment
variable `KAS_WORK_DIR`.


Use Cases
---------

1.  Initial build/setup::

    $ mkdir $PROJECT_DIR
    $ cd $PROJECT_DIR
    $ git clone $PROJECT_URL meta-project
    $ kas build meta-project/kas-project.yml

2.  Update/rebuild::

    $ cd $PROJECT_DIR/meta-project
    $ git pull
    $ kas build kas-project.yml

3.  Interactive configuration::

    $ cd $PROJECT_DIR/meta-project
    $ kas menu
    $ kas build  # optional, if not triggered via kas menu


Plugins
-------

kas sub-commands are implemented by a series of plugins. Each plugin
typically provides a single command.

.. only:: html

  ``build`` plugin
  ~~~~~~~~~~~~~~~~

  .. include:: userguide/plugins/build.inc

  ``checkout`` plugin
  ~~~~~~~~~~~~~~~~~~~

  .. include:: userguide/plugins/checkout.inc

  ``dump`` plugin
  ~~~~~~~~~~~~~~~

  .. include:: userguide/plugins/dump.inc

  ``for-all-repos`` plugin
  ~~~~~~~~~~~~~~~~~~~~~~~~

  .. include:: userguide/plugins/for-all-repos.inc

  ``menu`` plugin
  ~~~~~~~~~~~~~~~

  .. include:: userguide/plugins/menu.inc

  ``shell`` plugin
  ~~~~~~~~~~~~~~~~

  .. include:: userguide/plugins/shell.inc


Project Configuration
---------------------

.. only:: html

  .. include:: userguide/project-configuration.inc

.. _checkout-creds-label:

Credential Handling
-------------------

KAS provides various mechanisms to inject credentials into the build. By
using :ref:`env-vars-label`, a fine grained control is possible. All
credentials are made available both to KAS, as well as inside the build
environment. However, not all mechanisms are natively supported by all tools.
As KAS might need to modify credentials and config files, these are copied
into the isolated environment first. One exception is the SSH folder, where
changes are only performed if not yet present on the host.

AWS Configuration
~~~~~~~~~~~~~~~~~

For AWS, both conventional AWS config files as well as the environment
variable controlled OAuth 2.0 workflow are supported. Note, that KAS
internally rewrites the ``AWS_*`` environment variables into a AWS
config file to also support older versions of bitbake.

Git Configuration
~~~~~~~~~~~~~~~~~

A ``.gitconfig`` file can be used to provide credentials as well as
url rewrites of git repositories (``insteadof``). To support the patching
of git repositories, KAS injects a ``[user]`` section, possibly overwriting
an existing one. When running in the Github CI, the ``.gitconfig`` file is
automatically injected. In addition, credential helpers can be used by
setting the corresponding environment variables. These are added to the
``.gitconfig`` file as well.

Netrc File
~~~~~~~~~~

A ``.netrc`` file can be used to provide credentials for git or the
HTTP(S) / FTP fetcher. When running in the Gitlab CI, the ``CI_JOB_TOKEN``
is appended to automatically grant access to repositories that can be
accessed by the user that triggered the CI pipeline.

SSH
~~~

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
