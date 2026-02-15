#!/bin/bash
#
# ╔════════════════════════════════════════════════════════════════════════╗
# ║                                                                        ║
# ║   🧹 Varedura — Instalador Standalone v1.0.0                          ║
# ║   Monitor de Sistema & Ferramenta de Limpeza Docker                    ║
# ║                                                                        ║
# ║   GitHub: https://github.com/joaosnet/Varedura                        ║
# ║                                                                        ║
# ╚════════════════════════════════════════════════════════════════════════╝
#
# Usage / Uso:
#   curl -fsSL https://raw.githubusercontent.com/joaosnet/Varedura/main/install.sh | bash
#   or: chmod +x install.sh && ./install.sh
#
#   Flags:
#     --uninstall    Remove varedura from the system
#     --check        Check dependencies only
#     --lang en      Force English output
#     --lang pt      Force Portuguese output
#

set -e

# ═══════════════════════════ TTY Detection ════════════════════════════════
if [ -t 0 ]; then
    TTY_INPUT="/dev/stdin"
else
    TTY_INPUT="/dev/tty"
fi

# ═══════════════════════════ Colors ═══════════════════════════════════════
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# ═══════════════════════════ Config ═══════════════════════════════════════
APP_NAME="varedura"
APP_VERSION="1.0.0"
REPO_URL="https://github.com/joaosnet/Varedura.git"
REPO_RAW="https://raw.githubusercontent.com/joaosnet/Varedura/main"
MIN_PYTHON="3.14"

# ═══════════════════════════ Language ═════════════════════════════════════
detect_lang() {
    local sys_lang="${LANG:-${LC_ALL:-${LC_MESSAGES:-en}}}"
    case "$sys_lang" in
        pt*) echo "pt" ;;
        *)   echo "en" ;;
    esac
}

INSTALLER_LANG="$(detect_lang)"

# Parse early flags
for arg in "$@"; do
    case "$arg" in
        --lang)  shift; INSTALLER_LANG="${1:-en}"; shift ;;
        --lang=*) INSTALLER_LANG="${arg#*=}" ;;
    esac
done

# ─── Bilingual messages ──────────────────────────────────────────────────
msg() {
    local key="$1"; shift
    local text=""

    if [ "$INSTALLER_LANG" = "pt" ]; then
        case "$key" in
            detecting_os)       text="🔍 Detectando sistema operacional..." ;;
            os_detected)        text="   Sistema : $1 $2" ;;
            checking_deps)      text="\n🔍 Verificando dependências...\n" ;;
            found)              text="   ✅ $1" ;;
            missing)            text="   ❌ $1 — não encontrado" ;;
            missing_optional)   text="   ⚠️  $1 — não encontrado (opcional)" ;;
            will_install)       text="   📦 $1 será instalado automaticamente" ;;
            installing_dep)     text="\n📦 Instalando $1..." ;;
            dep_ok)             text="   ✅ $1 instalado com sucesso" ;;
            installing_app)     text="\n📦 Instalando Varedura..." ;;
            install_progress)   text="   ⏳ Isso pode levar alguns minutos..." ;;
            already_installed)  text="\n⚠️  Varedura já está instalado." ;;
            choose_action)      text="   O que deseja fazer?\n\n   ${BOLD}[R]${NC} Reinstalar   ${BOLD}[U]${NC} Desinstalar   ${BOLD}[C]${NC} Cancelar\n" ;;
            confirm_install)    text="\nDeseja prosseguir com a instalação? [S/n]: " ;;
            uninstalling)       text="\n🗑️  Desinstalando Varedura..." ;;
            uninstall_ok)       text="\n✅ Varedura desinstalado com sucesso." ;;
            not_installed)      text="\n⚠️  Varedura não está instalado." ;;
            abort)              text="\n❌ Operação cancelada." ;;
            error)              text="\n❌ Erro: $1" ;;
            summary_hdr)        text="\n📋 Resumo da instalação:" ;;
            sum_os)             text="   • Sistema       : $1" ;;
            sum_install)        text="   • A instalar    : $1" ;;
            sum_ok)             text="   • Já presente   : $1" ;;
            restart_hint)       text="\n💡 Reinicie o terminal para que o comando 'varedura' funcione." ;;
            path_hint)          text="💡 Certifique-se de que $1 está no seu PATH." ;;
            unsupported_os)     text="❌ Sistema operacional não suportado: $1" ;;
            uv_manages_py)      text="(uv gerencia a versão automaticamente)" ;;
            check_ready)        text="\n✅ Todas as dependências obrigatórias estão presentes." ;;
            check_missing)      text="\n❌ Dependências obrigatórias faltando: $1" ;;
        esac
    else
        case "$key" in
            detecting_os)       text="🔍 Detecting operating system..." ;;
            os_detected)        text="   System  : $1 $2" ;;
            checking_deps)      text="\n🔍 Checking dependencies...\n" ;;
            found)              text="   ✅ $1" ;;
            missing)            text="   ❌ $1 — not found" ;;
            missing_optional)   text="   ⚠️  $1 — not found (optional)" ;;
            will_install)       text="   📦 $1 will be installed automatically" ;;
            installing_dep)     text="\n📦 Installing $1..." ;;
            dep_ok)             text="   ✅ $1 installed successfully" ;;
            installing_app)     text="\n📦 Installing Varedura..." ;;
            install_progress)   text="   ⏳ This may take a few minutes..." ;;
            already_installed)  text="\n⚠️  Varedura is already installed." ;;
            choose_action)      text="   What would you like to do?\n\n   ${BOLD}[R]${NC} Reinstall   ${BOLD}[U]${NC} Uninstall   ${BOLD}[C]${NC} Cancel\n" ;;
            confirm_install)    text="\nProceed with installation? [Y/n]: " ;;
            uninstalling)       text="\n🗑️  Uninstalling Varedura..." ;;
            uninstall_ok)       text="\n✅ Varedura uninstalled successfully." ;;
            not_installed)      text="\n⚠️  Varedura is not installed." ;;
            abort)              text="\n❌ Operation cancelled." ;;
            error)              text="\n❌ Error: $1" ;;
            summary_hdr)        text="\n📋 Installation summary:" ;;
            sum_os)             text="   • System        : $1" ;;
            sum_install)        text="   • To install    : $1" ;;
            sum_ok)             text="   • Already there : $1" ;;
            restart_hint)       text="\n💡 Restart your terminal for the 'varedura' command to work." ;;
            path_hint)          text="💡 Make sure $1 is in your PATH." ;;
            unsupported_os)     text="❌ Unsupported operating system: $1" ;;
            uv_manages_py)      text="(uv manages the version automatically)" ;;
            check_ready)        text="\n✅ All required dependencies are present." ;;
            check_missing)      text="\n❌ Missing required dependencies: $1" ;;
        esac
    fi

    echo -e "$text"
}

# ═══════════════════════════ Banner ═══════════════════════════════════════
print_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'

    ██╗   ██╗ █████╗ ██████╗ ███████╗██████╗ ██╗   ██╗██████╗  █████╗
    ██║   ██║██╔══██╗██╔══██╗██╔════╝██╔══██╗██║   ██║██╔══██╗██╔══██╗
    ██║   ██║███████║██████╔╝█████╗  ██║  ██║██║   ██║██████╔╝███████║
    ╚██╗ ██╔╝██╔══██║██╔══██╗██╔══╝  ██║  ██║██║   ██║██╔══██╗██╔══██║
     ╚████╔╝ ██║  ██║██║  ██║███████╗██████╔╝╚██████╔╝██║  ██║██║  ██║
      ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝

EOF
    if [ "$INSTALLER_LANG" = "pt" ]; then
        echo -e "        🧹 Monitor de Sistema & Limpeza Docker — Instalador v${APP_VERSION}"
    else
        echo -e "        🧹 System Monitor & Docker Cleanup — Installer v${APP_VERSION}"
    fi
    echo -e "${NC}"
}

# ═══════════════════════════ Helpers ══════════════════════════════════════
cmd_exists() {
    command -v "$1" &>/dev/null
}

get_version() {
    local cmd="$1"
    "$cmd" --version 2>/dev/null | head -1 || echo ""
}

confirm_yes() {
    local prompt="$1"
    echo -en "${CYAN}${prompt}${NC}"
    local answer
    read answer < "$TTY_INPUT" || true
    answer="${answer:-y}"
    case "$answer" in
        [nN]*) return 1 ;;
        *)     return 0 ;;
    esac
}

ask_action() {
    msg choose_action
    echo -en "   ${CYAN}> ${NC}"
    local answer
    read answer < "$TTY_INPUT" || true
    case "$answer" in
        [rR]*) echo "reinstall" ;;
        [uU]*) echo "uninstall" ;;
        *)     echo "cancel" ;;
    esac
}

# ═══════════════════════════ OS Detection ═════════════════════════════════
OS_TYPE=""
OS_NAME=""
OS_ARCH=""
OS_DETAIL=""
PACKAGE_MANAGER=""

detect_os() {
    msg detecting_os

    OS_ARCH="$(uname -m)"

    case "$(uname -s)" in
        Linux*)
            OS_TYPE="linux"
            OS_NAME="Linux"
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                OS_DETAIL="${PRETTY_NAME:-$NAME $VERSION_ID}"
            else
                OS_DETAIL="$(uname -r)"
            fi
            # Detect package manager
            if cmd_exists apt-get;  then PACKAGE_MANAGER="apt"
            elif cmd_exists dnf;    then PACKAGE_MANAGER="dnf"
            elif cmd_exists yum;    then PACKAGE_MANAGER="yum"
            elif cmd_exists pacman; then PACKAGE_MANAGER="pacman"
            elif cmd_exists zypper; then PACKAGE_MANAGER="zypper"
            elif cmd_exists apk;    then PACKAGE_MANAGER="apk"
            fi
            ;;
        Darwin*)
            OS_TYPE="macos"
            OS_NAME="macOS"
            OS_DETAIL="macOS $(sw_vers -productVersion 2>/dev/null || echo 'unknown')"
            PACKAGE_MANAGER="brew"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            OS_TYPE="windows"
            OS_NAME="Windows"
            OS_DETAIL="Windows (Git Bash)"
            ;;
        *)
            msg unsupported_os "$(uname -s)"
            exit 1
            ;;
    esac

    msg os_detected "$OS_NAME $OS_ARCH" "($OS_DETAIL)"
}

# ═══════════════════════════ Dependency Check ═════════════════════════════
TO_INSTALL=""
ALREADY_OK=""

check_dependencies() {
    msg checking_deps

    TO_INSTALL=""
    ALREADY_OK=""

    # ── Python ──
    if cmd_exists python3; then
        local py_ver
        py_ver="$(python3 --version 2>&1 | awk '{print $2}')"
        local py_major py_minor
        py_major="$(echo "$py_ver" | cut -d. -f1)"
        py_minor="$(echo "$py_ver" | cut -d. -f2)"
        if [ "$py_major" -ge 3 ] && [ "$py_minor" -ge 14 ]; then
            msg found "Python              ($py_ver)"
        else
            msg found "Python              ($py_ver) — $(msg uv_manages_py)"
        fi
        ALREADY_OK="${ALREADY_OK:+$ALREADY_OK, }Python"
    elif cmd_exists python; then
        local py_ver
        py_ver="$(python --version 2>&1 | awk '{print $2}')"
        msg found "Python              ($py_ver) — $(msg uv_manages_py)"
        ALREADY_OK="${ALREADY_OK:+$ALREADY_OK, }Python"
    else
        msg found "Python              — $(msg uv_manages_py)"
    fi

    # ── uv ──
    if cmd_exists uv; then
        local uv_ver
        uv_ver="$(get_version uv)"
        msg found "uv                  ($uv_ver)"
        ALREADY_OK="${ALREADY_OK:+$ALREADY_OK, }uv"
    else
        msg missing "uv (package manager)"
        msg will_install "uv"
        TO_INSTALL="${TO_INSTALL:+$TO_INSTALL, }uv"
    fi

    # ── Docker (optional) ──
    if cmd_exists docker; then
        local docker_ver
        docker_ver="$(get_version docker)"
        msg found "Docker              ($docker_ver)"
        ALREADY_OK="${ALREADY_OK:+$ALREADY_OK, }Docker"
    else
        msg missing_optional "Docker"
    fi

    # ── Git (optional) ──
    if cmd_exists git; then
        local git_ver
        git_ver="$(get_version git)"
        msg found "Git                 ($git_ver)"
        ALREADY_OK="${ALREADY_OK:+$ALREADY_OK, }Git"
    else
        msg missing_optional "Git"
    fi
}

# ═══════════════════════════ Installation ═════════════════════════════════
refresh_path() {
    local home_dir="${HOME:-$(eval echo ~)}"
    for p in "$home_dir/.local/bin" "$home_dir/.cargo/bin" "/usr/local/bin"; do
        if [ -d "$p" ]; then
            case ":$PATH:" in
                *":$p:"*) ;;
                *) export PATH="$p:$PATH" ;;
            esac
        fi
    done
}

install_uv() {
    msg installing_dep "uv"

    if [ "$OS_TYPE" = "macos" ] && cmd_exists brew; then
        brew install uv >/dev/null 2>&1 || true
    fi

    if ! cmd_exists uv; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi

    refresh_path

    if cmd_exists uv; then
        local ver
        ver="$(get_version uv)"
        msg dep_ok "uv ($ver)"
        return 0
    fi

    msg restart_hint
    return 0
}

install_varedura() {
    msg installing_app
    msg install_progress

    local source=""
    # If running from within the repo, install local
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
    if [ -f "$script_dir/pyproject.toml" ]; then
        source="$script_dir"
    else
        source="git+${REPO_URL}"
    fi

    local uv_cmd
    uv_cmd="$(command -v uv || echo "uv")"

    if "$uv_cmd" tool install "$source" --force --python ">=3.14" 2>&1; then
        refresh_path
        return 0
    else
        msg error "uv tool install failed"
        return 1
    fi
}

uninstall_varedura() {
    msg uninstalling

    local uv_cmd
    uv_cmd="$(command -v uv || echo "uv")"

    if "$uv_cmd" tool uninstall "$APP_NAME" 2>&1; then
        msg uninstall_ok
        return 0
    else
        msg error "uv tool uninstall failed"
        return 1
    fi
}

is_installed() {
    refresh_path
    cmd_exists "$APP_NAME"
}

# ═══════════════════════════ Success Banner ═══════════════════════════════
print_success() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    if [ "$INSTALLER_LANG" = "pt" ]; then
        echo -e "${GREEN}║   ✅  Varedura instalado com sucesso!            ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "   Digite ${BOLD}${CYAN}varedura${NC} no terminal para iniciar."
    else
        echo -e "${GREEN}║   ✅  Varedura installed successfully!           ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "   Type ${BOLD}${CYAN}varedura${NC} in the terminal to start."
    fi
    echo ""
}

# ═══════════════════════════ Main Flows ═══════════════════════════════════
do_check() {
    detect_os
    check_dependencies

    if [ -n "$TO_INSTALL" ]; then
        msg check_missing "$TO_INSTALL"
        return 1
    else
        msg check_ready
        return 0
    fi
}

do_uninstall() {
    if ! is_installed; then
        msg not_installed
        return 1
    fi
    uninstall_varedura
}

do_install() {
    # Already installed?
    if is_installed; then
        msg already_installed
        local action
        action="$(ask_action)"
        case "$action" in
            reinstall) ;;  # continue
            uninstall) uninstall_varedura; return $? ;;
            *)         msg abort; return 0 ;;
        esac
    fi

    # 1. Detect OS
    detect_os

    # 2. Check dependencies
    check_dependencies

    # 3. Summary
    msg summary_hdr
    msg sum_os "$OS_NAME $OS_ARCH"
    local install_items="${TO_INSTALL:+$TO_INSTALL, }${APP_NAME}"
    msg sum_install "$install_items"
    [ -n "$ALREADY_OK" ] && msg sum_ok "$ALREADY_OK"

    # 4. Confirm
    if ! confirm_yes "$(msg confirm_install)"; then
        msg abort
        return 0
    fi

    # 5. Install uv if needed
    if echo "$TO_INSTALL" | grep -q "uv"; then
        install_uv || return 1
    fi

    # 6. Install varedura
    install_varedura || return 1

    # 7. Success
    print_success

    refresh_path
    if ! cmd_exists "$APP_NAME"; then
        msg path_hint "\$HOME/.local/bin"
        msg restart_hint
    fi

    return 0
}

# ═══════════════════════════ Entry Point ══════════════════════════════════
main() {
    local mode="install"

    for arg in "$@"; do
        case "$arg" in
            --uninstall) mode="uninstall" ;;
            --check)     mode="check" ;;
            --lang)      ;; # already parsed
            --lang=*)    ;; # already parsed
            --help|-h)
                echo "Usage: $0 [--uninstall] [--check] [--lang pt|en]"
                exit 0
                ;;
        esac
    done

    print_banner

    case "$mode" in
        check)     do_check ;;
        uninstall) do_uninstall ;;
        install)   do_install ;;
    esac
}

main "$@"
