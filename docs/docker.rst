Docker Image usage
==================

See https://hub.docker.com/r/kasproject for all available images.

Precondition
------------

You need a local folder for data exchange between the container and your machine. Here is a good suggestion:

+-------+-----+----+------------------+--------------------+
| MyLocalKasFolder                                         |
+-------+-----+----+------------------+--------------------+
|   >   | workingDir                                       |
+-------+-----+----+------------------+--------------------+
|   >   | meta-my-project                                  |
+-------+-----+----+------------------+--------------------+
|   >   |  >  | kas-project.yml                            |
+-------+-----+----+------------------+--------------------+

Keep in mind the docker container need r/w access to all folders and files under **MyLocalKasFolder**

Starting the container
---------------

You need to `bind-mount <https://docs.docker.com/storage/bind-mounts/#start-a-container-with-a-bind-mount>`__ the local folder into your docker container.

``docker run -it --mount type=bind,source=<path to>/MyLocalKasFolder,target=/KAS kasproject/kas-isar:<version> sh``

Environment variables
---------------------

Now you can set your needed environment variable like described in https://raw.githubusercontent.com/siemens/kas/master/docs/userguide.rst

To use the local working dir we created above, you need to set the environment variable

``export KAS_WORKING_DIR=/KAS/workingDir``

Build
-----

Now you're ready to start your build

``kas build /KAS/meta-my-project/kas-project.yml``

See https://raw.githubusercontent.com/siemens/kas/master/docs/userguide.rst for details and more commands
