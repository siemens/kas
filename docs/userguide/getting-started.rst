Getting Started
===============

Installation
------------

pipx is the recommended way to install kas. It creates an isolated Python
virtual environment for kas and makes sure its dependencies are installed
correctly. To install pipx, follow the instructions at
https://pipx.pypa.io/stable/installation/

To install the latest version of kas using pipx run::

    $ pipx install kas

With menu support
~~~~~~~~~~~~~~~~~

kas menu requires an additional system dependency. On Debian-based systems,
run::

    $ sudo apt install python3-newt
    $ pipx install kas --system-site-packages

Other installation methods
~~~~~~~~~~~~~~~~~~~~~~~~~~

Debian-based distributions provide a package for kas. However, this may be
outdated compared to the latest release. To install kas using the system
package manager, run::

    $ sudo apt install kas

Dependencies
------------

This project depends on

- Python 3
- distro Python 3 package
- jsonschema Python 3 package
- PyYAML Python 3 package
- GitPython Python 3 package
- kconfiglib Python 3 package (optional, for menu plugin)
- NEWT Python 3 distro package (optional, for menu plugin)
- python-gnupg Python 3 package (optional, for signature verification)

Usage
-----

There are (at least) three options for using kas:

- Install it locally via pip to get the ``kas`` command.
- Use the container image locally. In this case, download the
  :doc:`kas-container <kas-container>` script from the kas repository and
  use it in place of the ``kas`` command.
  The script version corresponds to the kas tool and the kas image version.
- Use the container image in CI. Specify
  ``ghcr.io/siemens/kas/kas[-isar][:<x.y>][-<distro-release>]`` in your CI
  script that requests a container image as runtime environment.

Start build::

    $ kas build /path/to/kas-project.yml

Alternatively, experienced bitbake users can invoke usual **bitbake** steps
manually, e.g.::

    $ kas shell /path/to/kas-project.yml -c 'bitbake dosfsutils-native'

For details about the kas input file(s), see
:ref:`project-configuration-label`. Example configurations can be found in
:ref:`example-configurations-label`.

Directory Layout
~~~~~~~~~~~~~~~~

When invoking kas, it places download and build artifacts in the current
directory by default. You can specify a different location using the
environment variable ``KAS_WORK_DIR``. Repositories managed by kas are stored
under their ``path`` (or ``name`` if ``path`` is not set). The build directory
is named ``build`` and is relative to ``KAS_WORK_DIR`` unless explicitly set
with ``KAS_BUILD_DIR``. Internal data that persists across executions is
prefixed with ``.kas_``.


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
