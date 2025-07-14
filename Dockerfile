FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Base system & essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  wget \
  git \
  nano \
  less \
  tree \
  unzip \
  cron \
  openssh-server \
  build-essential \
  python3 \
  python3-pip \
  python3-venv \
  virtualenv \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Optional: Networking & diagnostics (uncomment for troubleshooting)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#   net-tools \
#   dnsutils \
#   nmap \
#   iperf3 \
#   tcpdump \
#   iftop \
#   bmon \
#   ncdu \
#   && apt-get clean && rm -rf /var/lib/apt/lists/*

# Optional: Monitoring & debugging tools (uncomment for troubleshooting)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#   lsof \
#   htop \
#   iotop \
#   strace \
#   && apt-get clean && rm -rf /var/lib/apt/lists/*

# File tools & automation (minimal + relevant for automation / n8n)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#   fd-find \
#   ripgrep \
#   moreutils \
#   && apt-get clean && rm -rf /var/lib/apt/lists/*

# Media & processing
RUN apt-get update && apt-get install -y --no-install-recommends \
  ffmpeg \
  ffprobe \
  sox \
  imagemagick \
  gifsicle \
  exiftool \
  poppler-utils \
  tesseract-ocr \
  aria2 \
  jq \
  yq \
  bc \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Fix fd symlink (fd-find on Debian/Ubuntu)
RUN ln -s $(which fdfind) /usr/local/bin/fd

# Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Gunicorn (for Flask web API)
RUN apt-get update && apt-get install -y --no-install-recommends python3-gunicorn && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Bootstrap files
COPY --chown=toolhubuser:user --chmod=755 scripts/ /bootstrap/scripts/
COPY --chown=toolhubuser:user --chmod=755 cron.d/ /bootstrap/cron.d/
COPY --chown=toolhubuser:user --chmod=755 logs/ /bootstrap/logs/
COPY --chown=toolhubuser:user --chmod=755 start.sh /start.sh

# Cleanup Windows line endings
RUN sed -i 's/\r$//' /start.sh && \
    find /bootstrap/scripts -type f \( -name "*.sh" -o -name "*.py" \) -exec sed -i 's/\r$//' {} \;

# Set permissions
RUN chmod -R 755 /bootstrap

ENV PATH="/scripts:$PATH"

# SSH configuration
RUN mkdir /var/run/sshd && \
  echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
  echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

# Generate SSH host keys
RUN ssh-keygen -A

WORKDIR /workspace
EXPOSE 22 5656
CMD ["bash", "/start.sh"]