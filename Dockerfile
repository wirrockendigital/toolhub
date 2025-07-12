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

# Python-Abhängigkeiten
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Bootstrap-Dateien kopieren mit korrekten Rechten
COPY --chown=toolhubuser:toolhubuser --chmod=755 scripts/ /bootstrap/scripts/
COPY --chown=toolhubuser:toolhubuser --chmod=755 cron.d/ /bootstrap/cron.d/
COPY --chown=toolhubuser:toolhubuser --chmod=755 logs/ /bootstrap/logs/
COPY --chown=toolhubuser:toolhubuser --chmod=755 start.sh /start.sh

# Zeilenumbrüche entfernen aus Shell- und Python-Dateien
RUN sed -i 's/\r$//' /start.sh && \
    find /bootstrap/scripts -type f \( -name "*.sh" -o -name "*.py" \) -exec sed -i 's/\r$//' {} \;

# Bootstrap-Verzeichnis vollständig lesbar machen (Sicherheit vs. Komfort)
RUN chmod -R 755 /bootstrap

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