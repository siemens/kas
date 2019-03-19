# This image builds Isar jobs using the kas tool

FROM kasproject/kas:latest

ENV LC_ALL=en_US.UTF-8
RUN echo 'deb http://deb.debian.org/debian buster main' > /etc/apt/sources.list.d/buster.list && \
    echo "Package: qemu-user-static binfmt-support\nPin: release n=buster\nPin-Priority: 501\n\nPackage: *\nPin: release n=buster\nPin-Priority: -1" > /etc/apt/preferences.d/qemu-user-static && \
    apt-get update && \
    apt-get install -y -f --no-install-recommends \
            autoconf automake gdisk libtool bash-completion \
            sudo grub2 grub-efi-amd64-bin grub-efi-ia32-bin \
            reprepro python3 binfmt-support e2fsprogs \
            multistrap qemu-user-static debootstrap && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp*

RUN echo "builder ALL=NOPASSWD: ALL" > /etc/sudoers.d/builder-nopasswd && \
    chmod 660 /etc/sudoers.d/builder-nopasswd

RUN echo "Defaults env_keep += \"ftp_proxy http_proxy https_proxy no_proxy\"" \
    > /etc/sudoers.d/env_keep && chmod 660 /etc/sudoers.d/env_keep

RUN sed -i 's|#!/bin/bash|\0\n\ndpkg-reconfigure qemu-user-static 2>\&1 \| grep -v "already enabled in kernel"|' /kas/docker-entrypoint
