User Guide
==========

Dependencies & installation
---------------------------

This project depends on

- Python 3
- distro Python 3 package
- jsonschema Python 3 package
- PyYAML Python 3 package (optional, for yaml file support)
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

``build`` plugin
~~~~~~~~~~~~~~~~

.. automodule:: kas.plugins.build

``checkout`` plugin
~~~~~~~~~~~~~~~~~~~

.. automodule:: kas.plugins.checkout

``for-all-repos`` plugin
~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: kas.plugins.for_all_repos

``menu`` plugin
~~~~~~~~~~~~~~~~

.. automodule:: kas.plugins.menu

``shell`` plugin
~~~~~~~~~~~~~~~~

.. automodule:: kas.plugins.shell


Project Configuration
---------------------

Currently, JSON and YAML are supported as the base file formats. Since YAML is
arguably easier to read, this documentation focuses on the YAML format.

.. code-block:: yaml

    # Every file needs to contain a header, that provides kas with information
    # about the context of this file.
    header:
      # The `version` entry in the header describes for which configuration
      # format version this file was created for. It is used by kas to figure
      # out if it is compatible with this file. The version is an integer that
      # is increased on every format change.
      version: x
    # The machine as it is written into the `local.conf` of bitbake.
    machine: qemux86-64
    # The distro name as it is written into the `local.conf` of bitbake.
    distro: poky
    repos:
      # This entry includes the repository where the config file is located
      # to the bblayers.conf:
      meta-custom:
      # Here we include a list of layers from the poky repository to the
      # bblayers.conf:
      poky:
        url: "https://git.yoctoproject.org/git/poky"
        refspec: 89e6c98d92887913cadf06b2adb97f26cde4849b
        layers:
          meta:
          meta-poky:
          meta-yocto-bsp:

A minimal input file consists out of the ``header``, ``machine``, ``distro``,
and ``repos``.

Additionally, you can add ``bblayers_conf_header`` and ``local_conf_header``
which are strings that are added to the head of the respective files
(``bblayers.conf`` or ``local.conf``):

.. code-block:: yaml

    bblayers_conf_header:
      meta-custom: |
        POKY_BBLAYERS_CONF_VERSION = "2"
        BBPATH = "${TOPDIR}"
        BBFILES ?= ""
    local_conf_header:
      meta-custom: |
        PATCHRESOLVE = "noop"
        CONF_VERSION = "1"
        IMAGE_FSTYPES = "tar"

``meta-custom`` in these examples should be a unique name (in project scope)
for this configuration entries. We assume that your configuration file is part
of a ``meta-custom`` repository/layer. This way its possible to overwrite or
append entries in files that include this configuration by naming an entry the
same (overwriting) or using an unused name (appending).

Including in-tree configuration files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's currently possible to include kas configuration files from the same
repository/layer like this:

.. code-block:: yaml

    header:
      version: x
      includes:
        - base.yml
        - bsp.yml
        - product.yml

The specified files are addressed relative to your current configuration file.

Including configuration files from other repos
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's also possible to include configuration files from other repos like this:

.. code-block:: yaml

    header:
      version: x
      includes:
        - repo: poky
          file: kas-poky.yml
        - repo: meta-bsp-collection
          file: hw1/kas-hw-bsp1.yml
        - repo: meta-custom
          file: products/product.yml
    repos:
      meta-custom:
      meta-bsp-collection:
        url: "https://www.example.com/git/meta-bsp-collection"
        refspec: 3f786850e387550fdab836ed7e6dc881de23001b
        layers:
          # Additional to the layers that are added from this repository
          # in the hw1/kas-hw-bsp1.yml, we add here an additional bsp
          # meta layer:
          meta-custom-bsp:
      poky:
        url: "https://git.yoctoproject.org/git/poky"
        refspec: 89e6c98d92887913cadf06b2adb97f26cde4849b
        layers:
          # If `kas-poky.yml` adds the `meta-yocto-bsp` layer and we
          # do not want it in our bblayers for this project, we can
          # overwrite it by setting:
          meta-yocto-bsp: excluded

The files are addressed relative to the git repository path.

The include mechanism collects and merges the content from top to bottom and
depth first. That means that settings in one include file are overwritten
by settings in a latter include file and entries from the last include file can
be overwritten by the current file. While merging all the dictionaries are
merged recursively while preserving the order in which the entries are added to
the dictionary. This means that ``local_conf_header`` entries are added to the
``local.conf`` file in the same order in which they are defined in the
different include files. Note that the order of the configuration file entries
is not preserved within one include file, because the parser creates normal
unordered dictionaries.

Including configuration files via the command line
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When specifying the kas configuration file on the command line, additional
configurations can be included ad-hoc:

    $ kas build kas-base.yml:debug-image.yml:board.yml

This is equivalent to static inclusion from some kas-combined.yml like this:

.. code-block:: yaml

    header:
      version: x
      includes:
        - kas-base.yml
        - debug.image.yml
        - board.yml

Command line inclusion allows to create configurations on-demand, without the
need to write a kas configuration file for each possible combination.

Note that all configuration files combined via the command line either have to
come from the same repository or have to live outside of any versioning control.
kas will refuse any other combination in order to avoid complications and
configuration flaws that can easily emerge from them.

Configuration reference
~~~~~~~~~~~~~~~~~~~~~~~

* ``header``: dict [required]
    The header of every kas configuration file. It contains information about
    the context of the file.

  * ``version``: integer [required]
      Lets kas check if it is compatible with this file. See the
      :doc:`configuration format changelog <format-changelog>` for the
      format history and the latest available version.

  * ``includes``: list [optional]
      A list of configuration files this current file is based on. They are
      merged in order they are stated. So a latter one could overwrite
      settings from previous files. The current file can overwrite settings
      from every included file. An item in this list can have one of two types:

    * item: string
        The path to a kas configuration file, relative to the current file.

    * item: dict
        If files from other repositories should be included, choose this
        representation.

      * ``repo``: string [required]
          The id of the repository where the file is located. The repo
          needs to be defined in the ``repos`` dictionary as ``<repo-id>``.

      * ``file``: string [required]
          The path to the file relative to the root of the repository.

* ``build_system``: string [optional]
    Defines the bitbake-based build system. Known build systems are
    ``openembedded`` (or ``oe``) and ``isar``. If set, this restricts the
    search of kas for the init script in the configured repositories to
    ``oe-init-build-env`` or ``isar-init-build-env``, respectively. If
    ``kas-container`` finds this property in the top-level kas configuration
    file (includes are not evaluated), it will automatically select the
    required container image and invocation mode.

* ``defaults``: dict [optional]
    This key can be used to set default values for various properties.
    This may help you to avoid repeating the same property assignment in
    multiple places if, for example, you wish to use the same refspec for
    all repositories.

  * ``repos``: dict [optional]
      This key can contain default values for some repository properties.
      If a default value is set for a repository property it may still be
      overridden by setting the same property to a different value in a given
      repository.

    * ``refspec``: string [optional]
        Sets the default ``refspec`` property applied to all repositories that
        do not override this.

    * ``patches``: dict [optional]
        This key can contain default values for some repository patch
        properties. If a default value is set for a patch property it may
        still be overridden by setting the same property to a different value
        in a given patch.

      * ``repo``: string [optional]
          Sets the default ``repo`` property applied to all repository
          patches that do not override this.

* ``machine``: string [optional]
    Contains the value of the ``MACHINE`` variable that is written into the
    ``local.conf``. Can be overwritten by the ``KAS_MACHINE`` environment
    variable and defaults to ``qemux86-64``.

* ``distro``: string [optional]
    Contains the value of the ``DISTRO`` variable that is written into the
    ``local.conf``. Can be overwritten by the ``KAS_DISTRO`` environment
    variable and defaults to ``poky``.

* ``target``: string [optional] or list [optional]
    Contains the target or a list of targets to build by bitbake. Can be
    overwritten by the ``KAS_TARGET`` environment variable and defaults to
    ``core-image-minimal``. Space is used as a delimiter if multiple targets
    should be specified via the environment variable.

* ``env``: dict [optional]
    Contains environment variable names with the default values. These
    variables are made available to bitbake via ``BB_ENV_EXTRAWHITE`` and can
    be overwritten by the variables of the environment in which kas is started.

* ``task``: string [optional]
    Contains the task to build by bitbake. Can be overwritten by the
    ``KAS_TASK`` environment variable and defaults to ``build``.

* ``repos``: dict [optional]
    Contains the definitions of all available repos and layers.

  * ``<repo-id>``: dict [optional]
      Contains the definition of a repository and the layers, that should be
      part of the build. If the value is ``None``, the repository, where the
      current configuration file is located is defined as ``<repo-id>`` and
      added as a layer to the build.

    * ``name``: string [optional]
        Defines under which name the repository is stored. If its missing
        the ``<repo-id>`` will be used.

    * ``url``: string [optional]
        The url of the repository. If this is missing, no version control
        operations are performed.

    * ``type``: string [optional]
        The type of version control repository. The default value is ``git``
        and ``hg`` is also supported.

    * ``refspec``: string [optional]
        The refspec that should be used. If ``url`` was specified but no
        ``refspec`` the revision you get depends on the defaults of the version
        control system used.

    * ``path``: string [optional]
        The path where the repository is stored.
        If the ``url`` and ``path`` is missing, the repository where the
        current configuration file is located is defined.
        If the ``url`` is missing and the path defined, this entry references
        the directory the path points to.
        If the ``url`` as well as the ``path`` is defined, the path is used to
        overwrite the checkout directory, that defaults to ``kas_work_dir``
        + ``repo.name``.
        In case of a relative path name ``kas_work_dir`` is prepended.

    * ``layers``: dict [optional]
        Contains the layers from this repository that should be added to the
        ``bblayers.conf``. If this is missing or ``None`` or and empty
        dictionary, the path to the repo itself is added as a layer.

      * ``<layer-path>``: enum [optional]
          Adds the layer with ``<layer-path>`` that is relative to the
          repository root directory, to the ``bblayers.conf`` if the value of
          this entry is not in this list: ``['disabled', 'excluded', 'n', 'no',
          '0', 'false']``. This way it is possible to overwrite the inclusion
          of a layer in latter loaded configuration files.

    * ``patches``: dict [optional]
        Contains the patches that should be applied to this repo before it is
        used.

      * ``<patches-id>``: dict [optional]
          One entry in patches with its specific and unique id. All available
          patch entries are applied in the order of their sorted
          ``<patches-id>``.

        * ``repo``: string [required]
            The identifier of the repo where the path of this entry is relative
            to.

        * ``path``: string [required]
            The path to one patch file or a quilt formatted patchset directory.

* ``bblayers_conf_header``: dict [optional]
    This contains strings that should be added to the ``bblayers.conf`` before
    any layers are included.

  * ``<bblayers-conf-id>``: string [optional]
      A string that is added to the ``bblayers.conf``. The entry id
      (``<bblayers-conf-id>``) should be unique if lines should be added and
      can be the same from another included file, if this entry should be
      overwritten. The lines are added to ``bblayers.conf`` in the same order
      as they are included from the different configuration files.

* ``local_conf_header``: dict [optional]
    This contains strings that should be added to the ``local.conf``.

  * ``<local-conf-id>``: string [optional]
      A string that is added to the ``local.conf``. It operates in the same way
      as the ``bblayers_conf_header`` entry.

* ``menu_configuration``:: dict [optional]
    This contains user choices for a Kconfig menu of a project. Each variable
    corresponds to a Kconfig configuration variable and can be of the types
    string, boolean or integer. The content of this key is typically
    maintained by the ``kas menu`` plugin in a ``.config.yaml`` file.
