FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Base system & essentials
RUN apt-get update && apt-get install -y --no-install-recommends curl       # Command-line tool for HTTP requests
RUN apt-get install -y --no-install-recommends netbase                      # Provide /etc/protocols and /etc/services for networking CLIs
RUN apt-get install -y --no-install-recommends wget                         # Download files from the internet
RUN apt-get install -y --no-install-recommends git                          # Git version control
RUN apt-get install -y --no-install-recommends nano                         # Terminal text editor
RUN apt-get install -y --no-install-recommends less                         # View text files page by page
RUN apt-get install -y --no-install-recommends tree                         # Show directory structure as a tree
RUN apt-get install -y --no-install-recommends unzip                        # Extract .zip files
RUN apt-get install -y --no-install-recommends cron                         # Cron daemon for scheduled tasks
RUN apt-get install -y --no-install-recommends openssh-server               # SSH server
RUN apt-get install -y --no-install-recommends build-essential              # Essential C/C++ build tools
RUN apt-get install -y --no-install-recommends python3                      # Python interpreter
RUN apt-get install -y --no-install-recommends python3-pip                  # Python package installer
RUN apt-get install -y --no-install-recommends python3-venv                 # Python virtual environments
RUN apt-get install -y --no-install-recommends virtualenv                   # Legacy Python virtualenv tool

# Optional: Networking & diagnostics (uncomment for troubleshooting)
# RUN apt-get update && apt-get install -y --no-install-recommends net-tools     # ifconfig, netstat
# RUN apt-get install -y --no-install-recommends dnsutils                         # dig, nslookup
# RUN apt-get install -y --no-install-recommends nmap                             # Network scanner
# RUN apt-get install -y --no-install-recommends iperf3                           # Network bandwidth tester
# RUN apt-get install -y --no-install-recommends tcpdump                          # Network packet capture
# RUN apt-get install -y --no-install-recommends iftop                            # Live bandwidth usage
# RUN apt-get install -y --no-install-recommends bmon                             # Bandwidth monitor
# RUN apt-get install -y --no-install-recommends ncdu                             # Disk usage analyzer

# Optional: Monitoring & debugging tools (uncomment for troubleshooting)
# RUN apt-get update && apt-get install -y --no-install-recommends lsof          # List open files
# RUN apt-get install -y --no-install-recommends htop                             # Interactive process viewer
# RUN apt-get install -y --no-install-recommends iotop                            # Disk I/O monitor
# RUN apt-get install -y --no-install-recommends strace                           # Trace system calls

# File tools & automation (minimal + relevant for automation / n8n)
# RUN apt-get update && apt-get install -y --no-install-recommends fd-find       # Fast file search (fd)
# RUN apt-get install -y --no-install-recommends ripgrep                          # Recursive text search
# RUN apt-get install -y --no-install-recommends moreutils                        # Extra Unix tools (e.g. sponge)

# Media & processing
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg     # ffmpeg inkl. ffprobe
RUN apt-get install -y --no-install-recommends sox                           # Audio processing and conversion
RUN apt-get install -y --no-install-recommends imagemagick                   # Image manipulation
RUN apt-get install -y --no-install-recommends gifsicle                      # GIF image optimization
RUN apt-get install -y --no-install-recommends exiftool                      # Image metadata editing
RUN apt-get install -y --no-install-recommends poppler-utils                 # PDF utilities (e.g. pdftotext)
RUN apt-get install -y --no-install-recommends tesseract-ocr                 # OCR engine
RUN apt-get install -y --no-install-recommends aria2                         # Advanced CLI downloader
RUN apt-get install -y --no-install-recommends jq                            # JSON processor
RUN apt-get install -y --no-install-recommends yq                            # YAML processor
RUN apt-get install -y --no-install-recommends bc                            # Command-line calculator

RUN apt-get update && apt-get install -y --no-install-recommends wakeonlan && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create an fd compatibility symlink only when fdfind is installed.
RUN if command -v fdfind >/dev/null 2>&1; then ln -sf "$(command -v fdfind)" /usr/local/bin/fd; fi

# Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Ship Python tool modules inside the image so webhook/script wrappers work without a repo bind mount.
COPY tools/ /opt/toolhub/tools/
COPY mcp_tools/ /opt/toolhub/mcp_tools/
# Ensure copied sources are readable/executable for the non-root runtime user.
RUN chmod -R a+rX /opt/toolhub

# Gunicorn (for Flask web API)
RUN apt-get update && apt-get install -y --no-install-recommends python3-gunicorn && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Bootstrap files
COPY --chown=toolhubuser:user --chmod=755 scripts/ /bootstrap/scripts/
COPY --chown=toolhubuser:user --chmod=755 cron.d/ /bootstrap/cron.d/
COPY --chown=toolhubuser:user --chmod=755 start.sh /start.sh

# Cleanup Windows line endings
RUN sed -i 's/\r$//' /start.sh && \
    find /bootstrap/scripts -type f \( -name "*.sh" -o -name "*.py" \) -exec sed -i 's/\r$//' {} \;

# Set permissions
RUN chmod -R 755 /bootstrap

ENV PATH="/scripts:$PATH"
ENV TOOLHUB_PYTHON_ROOT="/opt/toolhub"

# SSH configuration
RUN mkdir /var/run/sshd && \
  echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
  echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

# Generate SSH host keys
RUN ssh-keygen -A

WORKDIR /workspace
EXPOSE 22 5656
CMD ["bash", "/start.sh"]
