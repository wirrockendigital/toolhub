FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Tools & CLI-Paketliste
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  wget \
  git \
  ffmpeg \
  jq \
  yq \
  unzip \
  imagemagick \
  sox \
  python3 \
  python3-pip \
  nano \
  less \
  net-tools \
  dnsutils \
  lsof \
  tree \
  htop \
  exiftool \
  bc \
  cron \
  openssh-server \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY --chown=toolhubuser:toolhubuser --chmod=755 scripts /bootstrap/scripts/
COPY --chown=toolhubuser:toolhubuser --chmod=755 cron.d /bootstrap/cron.d/
COPY --chown=toolhubuser:toolhubuser --chmod=755 logs /bootstrap/logs/
COPY --chown=toolhubuser:toolhubuser --chmod=755 start.sh /start.sh
RUN sed -i 's/\r$$//' /start.sh
RUN sed -i 's/\r$$//' /bootstrap/scripts/*.sh

ENV PATH="/scripts:$PATH"

# Benutzer anlegen
RUN useradd -m -u 1061 -s /bin/bash toolhubuser \
  && echo "toolhubuser:sj39fKF#dL92" | chpasswd

# SSH & Firewall konfigurieren
RUN mkdir /var/run/sshd \
  && echo "PermitRootLogin no" >> /etc/ssh/sshd_config \
  && echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

WORKDIR /workspace
EXPOSE 22 5656
USER toolhubuser
CMD ["bash", "/start.sh"]