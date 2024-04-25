Getting Started
===============

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
