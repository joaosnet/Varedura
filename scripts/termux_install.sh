#!/data/data/com.termux/files/usr/bin/bash
# Varedura — Idempotent installer for Termux (Android ARM64)
set -euo pipefail

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
CANDIDATE_REPO="$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)"

REPO_DIR=""
REPLACE_MENU=0
SKIP_APT=0

usage() {
    cat <<'EOF'
Uso: termux_install.sh [opcoes]

Opcoes:
  --repo-dir <caminho>   Diretorio do repositorio Varedura (padrao: pai do script ou ~/varedura)
  --replace-menu         Substitui $PREFIX/bin/menu mantendo backup em menu.m35.bak e $PREFIX/bin/m35-center intacto
  --skip-apt             Pula apt-get update/install (reinstalacao rapida apenas de Python/editable)
  -h, --help             Exibe esta ajuda
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --replace-menu)
            REPLACE_MENU=1
            shift
            ;;
        --skip-apt)
            SKIP_APT=1
            shift
            ;;
        --repo-dir)
            if [ "$#" -lt 2 ]; then
                echo "Erro: --repo-dir exige um argumento." >&2
                exit 2
            fi
            REPO_DIR="$2"
            shift 2
            ;;
        --repo-dir=*)
            REPO_DIR="${1#*=}"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Erro: opcao desconhecida '$1'." >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ -z "$REPO_DIR" ]; then
    if [ -f "$CANDIDATE_REPO/pyproject.toml" ]; then
        REPO_DIR="$CANDIDATE_REPO"
    else
        REPO_DIR="$HOME/varedura"
    fi
fi

case "$REPO_DIR" in
    "~") REPO_DIR="$HOME" ;;
    "~/"*) REPO_DIR="$HOME/${REPO_DIR#~/}" ;;
esac

if [ ! -d "$PREFIX/bin" ]; then
    echo "Erro: PREFIX invalido ($PREFIX). Execute este script dentro do Termux." >&2
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "Erro: apt-get nao encontrado. Verifique sua instalacao do Termux." >&2
    exit 1
fi

if [ ! -f "$REPO_DIR/pyproject.toml" ]; then
    echo "Erro: pyproject.toml nao encontrado em '$REPO_DIR'." >&2
    echo "Sincronize o repositorio primeiro (ex.: scripts/sync_termux_adb.ps1) ou informe --repo-dir." >&2
    exit 1
fi

echo "==> [1/4] Instalando pacotes nativos do Termux..."
if [ "$SKIP_APT" -eq 0 ]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        git python python-psutil matplotlib ffmpeg mpv nmap openssh termux-api termux-tools cronie
else
    echo "    (--skip-apt ativo: pulando apt-get)"
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Erro: python3 nao encontrado apos instalacao dos pacotes." >&2
    exit 1
fi

echo "==> [2/4] Instalando dependencias pure-Python..."
python3 -m pip install --upgrade \
    textual rich requests speedtest-cli reportlab pypdf2 truststore idna setuptools

echo "==> [3/4] Instalando Varedura em modo editavel ($REPO_DIR)..."
python3 -m pip install --no-build-isolation --no-deps -e "$REPO_DIR"

if [ "$REPLACE_MENU" -eq 1 ]; then
    echo "==> [4/4] Configurando launcher $PREFIX/bin/menu..."
    MENU_BIN="$PREFIX/bin/menu"
    MENU_BAK="$PREFIX/bin/menu.m35.bak"
    if [ -e "$MENU_BIN" ] && [ ! -e "$MENU_BAK" ]; then
        cp -p "$MENU_BIN" "$MENU_BAK"
        echo "    Backup criado em: $MENU_BAK"
    elif [ -e "$MENU_BAK" ]; then
        echo "    Backup existente preservado: $MENU_BAK"
    fi

    if [ -e "$PREFIX/bin/m35-center" ]; then
        echo "    $PREFIX/bin/m35-center preservado intacto."
    fi

    cat > "$MENU_BIN" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
shopt -s execfail
exec varedura "$@" || exec python3 "$HOME/.claro_suite/m35_tui.py" "$@"
EOF
    chmod 0755 "$MENU_BIN"
    echo "    Launcher atualizado: $MENU_BIN"
else
    echo "==> [4/4] --replace-menu nao informado; $PREFIX/bin/menu mantido intacto."
fi

echo ""
echo "Instalacao concluida com sucesso!"
echo ""
echo "Proximos passos:"
echo "  1. Execute 'varedura' para abrir a TUI Textual."
if [ "$REPLACE_MENU" -eq 1 ]; then
    echo "     (Ou execute 'menu'; o launcher legado continua acessivel via 'm35-center'.)"
fi
echo "  2. Para atualizacoes automaticas via Git (repositorio privado):"
echo "     Configure seu token localmente (nunca salve no .git/config) com:"
echo "       varedura-update --set-token"
echo "     Depois verifique com:"
echo "       varedura-update --status"
echo "       varedura-update --check"
echo "  3. Para agendar verificacao automatica a cada 6h via cronie:"
echo "       varedura-update --cron-on"
