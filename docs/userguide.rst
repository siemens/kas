User Guide
==========

.. only:: html

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

.. only:: html

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

.. only:: man

  :manpage:`kas-build(1)`
    build the project
  :manpage:`kas-checkout(1)`
    checkout all repos without building
  :manpage:`kas-dump(1)`
    dump the flattened configuration or lockfiles
  :manpage:`kas-for-all-repos(1)`
    run a command in each repository
  :manpage:`kas-menu(1)`
    interactive menu to configure the build
  :manpage:`kas-shell(1)`
    start a shell in the build environment

Project Configuration
---------------------

.. only:: html

  .. include:: userguide/project-configuration.inc

.. only:: man

  The project configuration file describes the build environment and the layers
  to be used. It is the main input to kas.
  For details, see :manpage:`kas-project-config(1)`

.. _checkout-creds-label:

Credential Handling
-------------------

.. only:: html

  .. include:: userguide/credentials.inc

.. only:: man

  kas provides various mechanisms to inject credentials into the build.
  For details, see :manpage:`kas-credentials(1)`.
