Developer Guide
===============

Deploy for development
----------------------

This project uses pip to manage the package. If you want to work on the
project yourself you can create the necessary links via::

    $ pip3 install --user -e .

That will install a backlink ~/.local/bin/kas to this project. Now you are
able to call it from anywhere.


Docker image build
------------------

For the Yocto/OE build image, just run::

    $ docker build -t <kas_image_name> .

For the Yocto/OE build image, use::

    $ docker build --target kas-isar -t <kas-isar_image_name> .

When you need a proxy to access the internet, add::

    --build-arg http_proxy=<http_proxy> --build-arg https_proxy=<https_proxy>
    --build-arg ftp_proxy=<ftp_proxy> --build-arg no_proxy=<no_proxy>

to the call.


Community Resources
-------------------

Project home:

 - https://github.com/siemens/kas

Source code:

 - https://github.com/siemens/kas.git
 - git@github.com:siemens/kas.git

Documentation:

 - https://kas.readthedocs.org

Mailing list:

  - kas-devel@googlegroups.com

  - Subscription:

    - kas-devel+subscribe@googlegroups.com
    - https://groups.google.com/forum/#!forum/kas-devel/join

  - Archives

    - https://groups.google.com/forum/#!forum/kas-devel
    - https://www.mail-archive.com/kas-devel@googlegroups.com/

Class reference documentation
-----------------------------

``kas.kas`` Module
..................

.. automodule:: kas.kas
   :members:

``kas.libkas`` Module
.....................

.. automodule:: kas.libkas
   :members:

``kas.libcmds`` Module
......................

.. automodule:: kas.libcmds
   :members:

``kas.config`` Module
.....................

.. automodule:: kas.config
   :members:

``kas.repos`` Module
....................

.. automodule:: kas.repos
   :members:

``kas.includehandler`` Module
.............................

.. automodule:: kas.includehandler
   :members:

``kas.kasusererror`` Module
.............................

.. automodule:: kas.kasusererror
   :members:

``kas.plugins`` Module
......................

.. automodule:: kas.plugins
   :members:
