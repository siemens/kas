# This image builds Yocto 2.2 jobs using the kas tool

FROM debian:jessie-slim

ENV LOCALE=en_US.UTF-8
RUN apt-get update && \
    apt-get install -y locales && \
    sed -i -e "s/# $LOCALE.*/$LOCALE UTF-8/" /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    apt-get -y install gawk wget git-core diffstat unzip \
                       texinfo gcc-multilib build-essential \
                       chrpath socat cpio python python3 \
                       tar bzip2 curl dosfstools mtools parted \
                       syslinux tree python3-pip bc python3-yaml \
                       lsb-release && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN wget -nv -O /usr/bin/gosu "https://github.com/tianon/gosu/releases/download/1.10/gosu-amd64" && \
    chmod +x /usr/bin/gosu

COPY . /kas
RUN pip3 install /kas

ENTRYPOINT ["/kas/docker-entrypoint"]
