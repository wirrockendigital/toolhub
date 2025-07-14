FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Base system & essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \                        # Command-line tool for HTTP requests
  wget \                        # Download files from the internet
  git \                         # Git version control
  nano \                        # Terminal text editor
  less \                        # View text files page by page
  tree \                        # Show directory structure as a tree
  unzip \                       # Extract .zip files
  cron \                        # Cron daemon for scheduled tasks
  openssh-server \              # SSH server
  build-essential \             # Essential C/C++ build tools
  python3 \                     # Python interpreter
  python3-pip \                 # Python package installer
  python3-venv \                # Python virtual environments
  virtualenv \                  # Legacy Python virtualenv tool
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Optional: Networking & diagnostics (uncomment for troubleshooting)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#   net-tools \                    # ifconfig, netstat, etc.
#   dnsutils \                     # dig, nslookup
#   nmap \                         # Network scanner
#   iperf3 \                       # Network bandwidth tester
#   tcpdump \                      # Network packet capture
#   iftop \                        # Live bandwidth usage
#   bmon \                         # Bandwidth monitor
#   ncdu \                         # Disk usage viewer
#   && apt-get clean && rm -rf /var/lib/apt/lists/*

# Optional: Monitoring & debugging tools (uncomment for troubleshooting)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#   lsof \                        # List open files and sockets
#   htop \                        # Interactive process viewer
#   iotop \                       # Disk I/O monitor
#   strace \                      # Trace system calls and signals
#   && apt-get clean && rm -rf /var/lib/apt/lists/*

# File tools & automation (minimal + relevant for automation / n8n)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#   fd-find \                      # Simple, fast file search (fd)
#   ripgrep \                      # Fast recursive text search
#   moreutils \                    # Useful shell tools like sponge, ts, etc.
#   && apt-get clean && rm -rf /var/lib/apt/lists/*

# Media & processing
RUN apt-get update && apt-get install -y --no-install-recommends \
  ffmpeg \                      # Audio/video processing
  ffprobe \                     # Extract metadata from media files
  sox \                         # Audio processing and conversion
  imagemagick \                 # Image manipulation
  gifsicle \                    # GIF image optimization
  exiftool \                    # Read/write image metadata
  poppler-utils \               # PDF text/image extraction
  tesseract-ocr \               # OCR engine
  aria2 \                       # Advanced download manager
  jq \                          # JSON CLI processor
  yq \                          # YAML CLI processor
  bc \                          # Command-line calculator
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