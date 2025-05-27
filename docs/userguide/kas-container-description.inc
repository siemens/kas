The ``kas-container`` script is a wrapper to run `kas` inside a build container.
It gives fine grained control over the data that is mapped into the build and
decouples the build environment from the host system. For details, see
:ref:`env-vars-label`. The wrapper also takes care of mounting the necessary
directories and setting up the environment variables inside the container.

.. note::
    The ``kas-container`` script has limited support for Git worktrees. Regular
    Git operations on the checked-out repository are supported. However, executing
    any ``git worktree ...`` command inside the container is not allowed.

By default ``kas-container`` uses the official images provided by the kas project:
``ghcr.io/siemens/kas/kas[-isar]:<version>``. To specify your own image set the
``KAS_CONTAINER_IMAGE`` environment variable. The ``kas-container`` script version
should match the kas version inside the container. If kas detects that is was called
from ``kas-container`` and the versions do not match, a warning is emitted. This
limitation might be lessened in the future, once a stable interface between
``kas-container`` and kas is introduced.

As container backends, Docker and
Podman are supported. To force the use of podman over docker, set
``KAS_CONTAINER_ENGINE=podman``. For details, see :ref:`env-vars-label`.

Running under docker in `rootless mode <https://docs.docker.com/engine/security/rootless/>`_
is partially supported. It is recommended to use a distinct ``KAS_WORK_DIR`` outside of the
calling directory (repo-dir), as kas temporarily changes the ownership of the working
directory during its operation. All files managed by kas (including the repos) must not be
written to from the host. To completely remove all data managed by kas, use
``kas-container purge``. This also restores the directory owners of the dirs passed to kas,
so they can be removed from the host.

.. note::
    The ISAR build system is not compatible with rootless execution. By that,
    we fall back to the system docker or podman instance.
