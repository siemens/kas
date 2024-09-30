The ``kas-container`` script is a wrapper to run `kas` inside a build container.
It gives fine grained control over the data that is mapped into the build and
decouples the build environment from the host system. The wrapper also takes care of
mounting the necessary directories and setting up the environment variables.

As container backends, Docker and Podman are supported.
To force the use of podman over docker, set ``KAS_CONTAINER_ENGINE=podman``.
