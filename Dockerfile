# This image builds Yocto jobs using the kas tool

FROM debian:buster-slim

ARG TARGETPLATFORM
ARG DEBIAN_FRONTEND=noninteractive

RUN echo 'deb http://deb.debian.org/debian buster-backports main' > /etc/apt/sources.list.d/buster-backports.list && \
    apt-get update && \
    apt-get install -y locales && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG=en_US.utf8

RUN apt-get install --no-install-recommends -y \
        gawk wget git-core diffstat unzip texinfo \
        build-essential chrpath socat cpio python python3 python3-pip python3-pexpect \
        xz-utils debianutils iputils-ping python3-git python3-jinja2 libegl1-mesa libsdl1.2-dev \
        pylint3 xterm \
        python3-setuptools python3-wheel python3-yaml python3-distro python3-jsonschema \
        gosu lsb-release file vim less procps tree tar bzip2 zstd bc tmux libncurses-dev \
        dosfstools mtools parted lz4 \
        git-lfs/buster-backports mercurial iproute2 ssh-client curl rsync gnupg awscli sudo jq && \
    if [ "$TARGETPLATFORM" = "linux/amd64" ]; then \
        apt-get install --no-install-recommends -y gcc-multilib syslinux; \
    fi && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY contrib/oe-git-proxy /usr/local/bin/
ENV GIT_PROXY_COMMAND="oe-git-proxy" \
    NO_PROXY="*"

COPY . /kas
RUN pip3 --proxy=$https_proxy install --no-deps /kas && kas --help

RUN echo "builder ALL=NOPASSWD: ALL" > /etc/sudoers.d/builder-nopasswd && \
    chmod 660 /etc/sudoers.d/builder-nopasswd

RUN echo "Defaults env_keep += \"ftp_proxy http_proxy https_proxy no_proxy\"" \
    > /etc/sudoers.d/env_keep && chmod 660 /etc/sudoers.d/env_keep

ENTRYPOINT ["/kas/container-entrypoint"]
