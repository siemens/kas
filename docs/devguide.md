Developer Guide
===============

Deploy for development
----------------------

This project uses pip to manage the package. If you want to work on the
project yourself you can create the necessary links via:

```sh
$ sudo pip3 install -e .
```

That will install a backlink /usr/bin/kas to this project. Now you are
able to call it from anywhere.


Docker image build
------------------

Just run

```sh
$ docker build -t <image_name> .
```

When you need a proxy to access the internet, add `--build-arg
http_proxy=<http_proxy> --build-arg https_proxy=<https_proxy>` to the
call.


Community Resources
-------------------

Project home:

 - https://github.com/siemens/kas

Source code:

 - https://github.com/siemens/kas.git
 - git@github.com:siemens/kas.git

Mailing list:

  - kas-devel@googlegroups.com

  - Subscription:
    - kas-devel+subscribe@googlegroups.com
    - https://groups.google.com/forum/#!forum/kas-devel/join

  - Archives
    - https://groups.google.com/forum/#!forum/kas-devel
    - https://www.mail-archive.com/kas-devel@googlegroups.com/
