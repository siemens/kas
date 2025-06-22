.. _project-configuration-label:

Project Configuration
=====================

Currently, JSON and YAML 1.1 are supported as the base file formats. Since YAML
is arguably easier to read, this documentation focuses on the YAML format.

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
        commit: 89e6c98d92887913cadf06b2adb97f26cde4849b
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

``meta-custom`` in these examples should be a unique name for this
configuration entries.

We recommend that this unique name is the **same** as the name of the
containing repository/layer to ease cross-project referencing.

In given examples we assume that your configuration file is part of a
``meta-custom`` repository/layer. This way it is possible to overwrite or
append entries in files that include this configuration by naming an entry
the same (overwriting) or using an unused name (appending).

.. note::
  kas internally uses ``PyYAML`` to parse YAML documents, inheriting its
  limitations. Notably, ``PyYAML`` only supports YAML 1.1 and does not
  correctly handle non-string keys in mappings. To avoid this issue, we
  recommend quoting keys of other types, such as octal numbers (``0001``),
  integers (``42``), booleans (``false``) and special values (``no``).

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

The paths to the files in the include list are either absolute, if they start
with a `/`, or relative.

If the path is relative and the configuration file is inside a repository,
then path is relative to the repositories base directory. If the
configuration file is not in a repository, then the path is relative to the
parent directory of the file.

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
        commit: 3f786850e387550fdab836ed7e6dc881de23001b
        layers:
          # Additional to the layers that are added from this repository
          # in the hw1/kas-hw-bsp1.yml, we add here an additional bsp
          # meta layer:
          meta-custom-bsp:
      poky:
        url: "https://git.yoctoproject.org/git/poky"
        commit: 89e6c98d92887913cadf06b2adb97f26cde4849b
        layers:
          # If `kas-poky.yml` adds the `meta-yocto-bsp` layer and we
          # do not want it in our bblayers for this project, we can
          # overwrite it by setting:
          meta-yocto-bsp: excluded

The files are addressed relative to the git repository path.

The include mechanism collects and merges the content from top to bottom and
depth first. That means that settings in one include file are overwritten
by settings in a latter include file and entries from the last include file can
be overwritten by the current file.

.. warning::
  The include mechanism does not support circular references with respect to
  the ``repos`` entries. By that, a (transitive) include file must not change
  the reference of the repository it is included from.

While merging, all the dictionaries are
merged recursively while preserving the order in which the entries are added to
the dictionary. This means that ``local_conf_header`` entries are added to the
``local.conf`` file in the same order in which they are defined in the
different include files. The ``header.version`` property is always set to the
highest version number found in the config files.

.. note::
  Internally kas iterates the repository checkout step until all referenced
  repositories are resolved (checked out). After each iteration, the (partial)
  configuration is merged and the next iteration is started. Once all
  repositories are available, the final configuration is build. Then, all
  remaining repositories are checked out.

Including configuration files via the command line
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When specifying the kas configuration file on the command line, additional
configurations can be included ad-hoc::

    $ kas build kas-base.yml:debug-image.yml:board.yml

This is equivalent to static inclusion from some ``kas-combined.yml`` like
this:

.. code-block:: yaml

    header:
      version: x
      includes:
        - kas-base.yml
        - debug.image.yml
        - board.yml

Command line inclusion allows one to create configurations on-demand, without
the need to write a kas configuration file for each possible combination.

All configuration files combined via the command line either have to
come from the same repository or have to live outside of any versioning control.
kas will refuse any other combination in order to avoid complications and
configuration flaws that can easily emerge from them.

.. note::
  Git submodules are considered to be part of the main repository. Hence,
  including config files from a submodule is supported. The repository root
  is always the root of the main repository (if under VCS) or the directory
  of the first kas config file otherwise.

Working with lockfiles
~~~~~~~~~~~~~~~~~~~~~~

kas supports the use of lockfiles to pinpoint repositories to exact commit ID
(e.g. SHA-1 refs for git). A lockfile hereby only overrides the commit ID
defined in a kas file. When performing the checkout operation (or any other
operation that performs a checkout), kas checks if a file named
``<filename>.lock.<ext>`` is found next to the currently processed kas file.
If this is found, kas loads this file right before processing the current one
(similar to an include file).

.. note::
  The locking logic applies to both files on the kas cmdline and include files.

The following example shows this mechanism for a file ``kas/kas-isar.yml``
and its corresponding lockfile ``kas/kas-isar.lock.yml``.

``kas/kas-isar.yml``:

.. code-block:: yaml

  # [...]
  repos:
    isar:
      url: https://github.com/ilbers/isar.git
      branch: next

``kas/kas-isar.lock.yml``:

.. code-block:: yaml

  header:
    version: 14
  overrides:
    repos:
      isar:
        commit: 0336610df8bb0adce76ef8c5a921c758efed9f45

The ``lock`` plugin provides helpers to simplify the creation and update
of lockfiles. For details, see the plugins documentation: :mod:`kas.plugins.lock`.

Configuration reference
~~~~~~~~~~~~~~~~~~~~~~~

``header``: dict [required]
  :kasschemadesc:`header`

  ``version``: integer [required]
    :kasschemadesc:`header.properties.version`
    See the :doc:`configuration format changelog <../format-changelog>` for the
    format history and the latest available version.

  ``includes``: list [optional]
    :kasschemadesc:`header.properties.includes`
    An item in this list can have one of two types:

    item: string
      :kasschemadesc:`header.properties.includes.items.anyOf[0]`

    item: dict
      :kasschemadesc:`header.properties.includes.items.anyOf[1]`

      ``repo``: string [required]
        :kasschemadesc:`header.properties.includes.items.anyOf[1].properties.repo`
        The repo needs to be defined in the ``repos`` dictionary as
        ``<repo-id>``.

      ``file``: string [required]
        :kasschemadesc:`header.properties.includes.items.anyOf[1].properties.file`

``build_system``: string [optional]
  :kasschemadesc:`build_system`
  Known build systems are
  ``openembedded`` (or ``oe``) and ``isar``. If set, this restricts the
  search of kas for the init script in the configured repositories to
  ``oe-init-build-env`` or ``isar-init-build-env``, respectively. If
  ``kas-container`` finds this property in the top-level kas configuration
  file (includes are not evaluated), it will automatically select the
  required container image and invocation mode.

``defaults``: dict [optional]
  :kasschemadesc:`defaults`
  This may help you to avoid repeating the same property assignment in
  multiple places if, for example, you wish to use the same branch for
  all repositories.

  ``repos``: dict [optional]
    :kasschemadesc:`defaults.properties.repos`
    If a default value is set for a repository property it may still be
    overridden by setting the same property to a different value in a given
    repository.

    ``branch``: string [optional]
      :kasschemadesc:`defaults.properties.repos.properties.branch`

    ``tag``: string [optional]
      :kasschemadesc:`defaults.properties.repos.properties.tag`

    ``patches``: dict [optional]
      :kasschemadesc:`defaults.properties.repos.properties.patches`
      If a default value is set for a patch property it may
      still be overridden by setting the same property to a different value
      in a given patch.

      ``repo``: string [optional]
        Sets the default ``repo`` property applied to all repository
        patches that do not override this.

``machine``: string [optional]
  :kasschemadesc:`machine`

``distro``: string [optional]
  :kasschemadesc:`distro`

``target``: string [optional] or list [optional]
  :kasschemadesc:`target`

``env``: dict [optional]
  :kasschemadesc:`env`
  Either a string or nothing (``null``) can be assigned as value.
  The former one serves as a default value whereas the latter one will lead
  to add the variable only to ``BB_ENV_PASSTHROUGH_ADDITIONS`` and not to
  the environment where kas is started. Please note, that ``null`` needs to
  be assigned as the nulltype (e.g. ``MYVAR: null``), not as 'null'.

``task``: string [optional]
  :kasschemadesc:`task`

``repos``: dict [optional]
  :kasschemadesc:`repos`

  ``<repo-id>``: dict [optional]
    :kasschemadesc:`repos.additionalProperties.anyOf[0]`

    ``name``: string [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.name`

    ``url``: string [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.url`

    ``type``: string [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.type`

    ``commit``: string [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.commit`

    ``branch``: string or nothing (``null``) [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.branch`

    ``tag``: string or nothing (``null``)  [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.tag`

    ``path``: string [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.path`
      If the ``url`` and ``path`` is missing, the repository where the
      current configuration file is located is defined.
      If the ``url`` is missing and the path defined, this entry references
      the directory the path points to.
      If the ``url`` as well as the ``path`` is defined, the path is used to
      overwrite the checkout directory, that defaults to ``kas_work_dir``
      + ``repo.name``.
      In case of a relative path name ``kas_work_dir`` is prepended.

    ``signed``: boolean [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.signed`

    ``allowed_signers``: list [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.allowed_signers`

    ``layers``: dict [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.layers`
      This allows combinations:

      .. code-block:: yaml

         repos:
           meta-foo:
             url: https://github.com/bar/meta-foo.git
             path: layers/meta-foo
             branch: master
             layers:
               .:
               contrib:

      This adds both ``layers/meta-foo`` and ``layers/meta-foo/contrib`` from
      the ``meta-foo`` repository to ``bblayers.conf``.

      ``<layer-path>``: enum [optional]
        Adds the layer with ``<layer-path>`` that is relative to the
        repository root directory, to the ``bblayers.conf`` if the value of
        this entry is not ``disabled``. This way it is possible to overwrite
        the inclusion of a layer in later loaded configuration files. To
        re-enable it, set it to nothing (``null``).

    ``patches``: dict [optional]
      :kasschemadesc:`repos.additionalProperties.anyOf[0].properties.patches`

      ``<patches-id>``: dict [optional]
        One entry in patches with its specific and unique id. All available
        patch entries are applied in the order of their sorted
        ``<patches-id>``.

        ``repo``: string [required]
          The identifier of the repo where the path of this entry is relative
          to.

        ``path``: string [required]
          The path to one patch file or a quilt formatted patchset directory.

``overrides``: dict [optional]
  :kasschemadesc:`overrides`

  ``repos``: dict [optional]
    Maps to the top-level ``repos`` entry.

    ``<repo-id>``: dict [optional]
      Maps to the ``<repo-id>`` entry.

    ``commit``: string [optional]
      Pinned commit ID which overrides the ``commit`` of the corresponding
      repo.

``bblayers_conf_header``: dict [optional]
  :kasschemadesc:`bblayers_conf_header`

  ``<bblayers-conf-id>``: string [optional]
    A string that is added to the ``bblayers.conf``. The entry id
    (``<bblayers-conf-id>``) should be unique if lines should be added and
    can be the same from another included file, if this entry should be
    overwritten. The lines are added to ``bblayers.conf`` in alphabetic order
    of ``<bblayers-conf-id>`` to ensure deterministic generation of config
    files.

``local_conf_header``: dict [optional]
  :kasschemadesc:`local_conf_header`

  ``<local-conf-id>``: string [optional]
    A string that is added to the ``local.conf``. It operates in the same way
    as the ``bblayers_conf_header`` entry.

``menu_configuration``: dict [optional]
  :kasschemadesc:`menu_configuration`
  Each variable
  corresponds to a Kconfig configuration variable and can be of the types
  string, boolean or integer. The content of this key is typically
  maintained by the ``kas menu`` plugin in a ``.config.yaml`` file.

``artifacts``: dict [optional]
  :kasschemadesc:`artifacts`
  Each key-value pair describes an identifier and a path relative to the kas
  build dir, whereby the path can contain wildcards like ``*``. Unix-style
  globbing is applied to all paths. In case no artifact is found, the build is
  considered successful, if not stated otherwise by the used plugin and mode
  of operation.

  .. note:: There are no further semantics attached to the identifiers (yet).
            Both the author and the consumer of the artifacts node need to
            agree on the semantics.

  Example:

  .. code-block:: yaml

      artifacts:
        disk-image: path/to/image.*.img
        firmware: path/to/firmware.bin
        swu: path/to/update.swu

``signers``: dict [optional]
  :kasschemadesc:`signers`

  This dict contains the public keys or certificates that are used to verify
  the authenticity of the repositories. In case of GPG keys, these are made
  available to the build environment as well by pointing the ``GNUPGHOME``
  environment variable to the local keystore.

  ``<signer_id>``: dict [optional]
    :kasschemadesc:`signers.additionalProperties`
    For each signer, a unique identifier is required. The ``<signer_id>`` is
    used to reference the entry in the ``allowed_signers`` entries.

    ``type``: enum [optional]
      :kasschemadesc:`signers.additionalProperties.properties.type`

    ``repo``: string [optional]
      :kasschemadesc:`signers.additionalProperties.properties.repo`

    ``path``: string [optional]
      :kasschemadesc:`signers.additionalProperties.properties.path`

    ``fingerprint``: string [optional]
      :kasschemadesc:`signers.additionalProperties.properties.fingerprint`

      **GPG key fingerprint**: The fingerprint can be obtained by running
      ``gpg --list-keys --with-fingerprint --keyid-format=long <KEYID>``.
      The needed string is the 40-character fingerprint without spaces.

      **SSH key fingerprint**: The fingerprint can be obtained by running
      ``ssh-keygen -lf key.pub | awk '{print $2}'``.

    ``gpg_keyserver``: string [optional]
      :kasschemadesc:`signers.additionalProperties.properties.gpg_keyserver`

``_source_dir``: string [optional]
  :kasschemadesc:`_source_dir`

``_source_dir_host``: string [optional]
  :kasschemadesc:`_source_dir_host`
  It provides the absolute path to the top repo
  outside of the container (on the host). This value is only evaluated by the
  ``kas-container`` script. It must not be set manually and might only be
  defined in the top-level ``.config.yaml`` file.

.. _example-configurations-label:

Example project configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following snippets show minimal but working project configurations for
both OpenEmbedded and ISAR based distributions.

OpenEmbedded
------------

.. literalinclude:: ../../examples/openembedded.yml
  :language: YAML
  :lines: 25-

ISAR
----

.. literalinclude:: ../../examples/isar.yml
  :language: YAML
  :lines: 25-
