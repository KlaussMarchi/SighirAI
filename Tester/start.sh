#!/usr/bin/env bash
# Sighir AI — inicialização no Linux/macOS (funciona também no Git Bash do Windows).
#
#   bash start.sh claude            abre o Claude Code (Sonnet 5, esforço alto, sem pedir permissão)
#   bash start.sh gemini            abre o Antigravity CLI (Gemini Pro High, sem pedir permissão)
#   bash start.sh gemini --dry-run  prepara tudo e só mostra o comando
#
# Instala o que faltar (Python, dependências, o próprio agente) e abre o agente nesta pasta.
cd "$(dirname "$0")" || exit 1
agent="${1:-claude}"
shift 2>/dev/null
case "$agent" in
    claude|gemini|agy) ;;
    *) echo "uso: bash start.sh [claude|gemini] [--dry-run] [--sem-prompt]"; exit 2 ;;
esac

findpy() {
    for c in python3 python; do
        if command -v "$c" >/dev/null 2>&1 && \
           "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
            echo "$c"
            return 0
        fi
    done
    return 1
}

if ! PY=$(findpy); then
    echo "[ .. ] Python 3.9+ não encontrado — instalando"
    SUDO=""
    [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"
    if command -v apt-get >/dev/null 2>&1; then
        $SUDO apt-get update -qq && $SUDO apt-get install -y python3 python3-venv python3-pip
    elif command -v dnf >/dev/null 2>&1; then
        $SUDO dnf install -y python3 python3-pip
    elif command -v yum >/dev/null 2>&1; then
        $SUDO yum install -y python3 python3-pip
    elif command -v pacman >/dev/null 2>&1; then
        $SUDO pacman -S --noconfirm python python-pip
    elif command -v zypper >/dev/null 2>&1; then
        $SUDO zypper --non-interactive install python3 python3-pip
    elif command -v apk >/dev/null 2>&1; then
        $SUDO apk add python3 py3-pip
    elif command -v brew >/dev/null 2>&1; then
        brew install python
    fi
    PY=$(findpy) || { echo "[ERRO] instale o Python 3.9+ e rode de novo"; exit 5; }
fi

exec "$PY" tools/boot.py start "$agent" "$@"
