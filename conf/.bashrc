

# ~/.bashrc für toolhubuser im Toolhub-Container

# Prompt verbessern
export PS1="\[\e[32m\]\u@\h \[\e[33m\]\w\[\e[0m\]\n$ "

# Standard-Aliase
alias ll='ls -alF --color=auto'
alias la='ls -A'
alias l='ls -CF'

# Schnellnavigation
alias ws='cd /workspace'
alias scr='cd /scripts'
alias logs='cd /logs && ls -lt'

# Tools
alias gs='git status'
alias gp='git pull'
alias py='python3'

# Logs live ansehen
alias watchwhlog='tail -f /logs/twebhook.log'
sssss