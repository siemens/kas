# This image builds Yocto jobs using the kas tool

FROM debian:bullseye-slim as kas-base

ARG TARGETPLATFORM
ARG DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.utf8
RUN apt-get update && \
    apt-get install -y locales && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    apt-get install --no-install-recommends -y \
        python3-pip python3-setuptools python3-wheel python3-yaml python3-distro python3-jsonschema python3-newt \
        gosu lsb-release file vim less procps tree tar bzip2 zstd pigz lz4 unzip tmux libncurses-dev \
        git-lfs mercurial iproute2 ssh-client telnet curl rsync gnupg awscli sudo \
        socat bash-completion && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY . /kas
RUN chmod -R o-w /kas

RUN pip3 --proxy=$https_proxy install --no-deps kconfiglib && \
    pip3 --proxy=$https_proxy install --no-deps /kas && kas --version && \
    rm -rf $(pip3 cache dir)

RUN ln -s /kas/contrib/oe-git-proxy /usr/bin/
ENV GIT_PROXY_COMMAND="oe-git-proxy" \
    NO_PROXY="*"

RUN echo "builder ALL=NOPASSWD: ALL" > /etc/sudoers.d/builder-nopasswd && \
    chmod 660 /etc/sudoers.d/builder-nopasswd

RUN echo "Defaults env_keep += \"ftp_proxy http_proxy https_proxy no_proxy\"" \
    > /etc/sudoers.d/env_keep && chmod 660 /etc/sudoers.d/env_keep

ENTRYPOINT ["/kas/container-entrypoint"]

FROM kas-base as kas-isar

# The install package list are actually taking 1:1 from their documentation,
# so there some packages that can already installed by other downstream layers.
# This will not change any image sizes on all the layers in use.
ENV LC_ALL=en_US.UTF-8
RUN apt-get update && \
    apt-get install -y -f --no-install-recommends \
            binfmt-support debootstrap dosfstools dpkg-dev gettext-base git \
            mtools parted python3 quilt qemu-user-static reprepro sudo \
            git-buildpackage pristine-tar sbuild schroot \
            umoci skopeo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN sed -i 's|\tGOSU="gosu builder"|\0\n\tsbuild-adduser builder >/dev/null 2>\&1|' /kas/container-entrypoint
RUN sed -i 's|#!/bin/bash|\0\n\nupdate-binfmts --enable \&\& [ -f /proc/sys/fs/binfmt_misc/status ]|' /kas/container-entrypoint

FROM kas-base as kas

# The install package list are actually taking 1:1 from their documentation,
# so there some packages that can already installed by other downstream layers.
# This will not change any image sizes on all the layers in use.
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        gawk wget git diffstat unzip texinfo \
        gcc build-essential chrpath socat cpio python3 python3-pip python3-pexpect \
        xz-utils debianutils iputils-ping python3-git python3-jinja2 libegl1-mesa libsdl1.2-dev \
        pylint3 xterm python3-subunit mesa-common-dev zstd liblz4-tool && \
    if [ "$TARGETPLATFORM" = "linux/amd64" ]; then \
        apt-get install --no-install-recommends -y gcc-multilib g++-multilib; \
    fi && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
