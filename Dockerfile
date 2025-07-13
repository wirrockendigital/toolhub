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
# Install Gunicorn for production WSGI server
RUN apt-get update && apt-get install -y --no-install-recommends python3-gunicorn && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Bootstrap-Dateien kopieren mit korrekten Rechten
COPY --chown=toolhubuser:user --chmod=755 scripts/ /bootstrap/scripts/
COPY --chown=toolhubuser:user --chmod=755 cron.d/ /bootstrap/cron.d/
COPY --chown=toolhubuser:user --chmod=755 logs/ /bootstrap/logs/
COPY --chown=toolhubuser:user --chmod=755 start.sh /start.sh

# Zeilenumbrüche entfernen aus Shell- und Python-Dateien
RUN sed -i 's/\r$//' /start.sh && \
    find /bootstrap/scripts -type f \( -name "*.sh" -o -name "*.py" \) -exec sed -i 's/\r$//' {} \;

# Bootstrap-Verzeichnis vollständig lesbar machen (Sicherheit vs. Komfort)
RUN chmod -R 755 /bootstrap

ENV PATH="/scripts:$PATH"


# SSH & Firewall konfigurieren
RUN mkdir /var/run/sshd \
  && echo "PermitRootLogin no" >> /etc/ssh/sshd_config \
  && echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

# Generate SSH host keys at build time
RUN ssh-keygen -A


WORKDIR /workspacew
EXPOSE 22 5656
CMD ["bash", "/start.sh"]