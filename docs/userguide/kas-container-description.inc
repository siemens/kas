The ``kas-container`` script is a wrapper to run `kas` inside a build container.
It gives fine grained control over the data that is mapped into the build and
decouples the build environment from the host system. The wrapper also takes care of
mounting the necessary directories and setting up the environment variables.

By default ``kas-container`` uses the official images provided by the kas project:
``ghcr.io/siemens/kas/kas[-isar]:<version>``. To specify your own image set the
``KAS_CONTAINER_IMAGE`` environment variable. As container backends, Docker and
Podman are supported. To force the use of podman over docker, set
``KAS_CONTAINER_ENGINE=podman``. For details, see :ref:`env-vars-label`.
