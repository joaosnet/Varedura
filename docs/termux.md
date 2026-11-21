# Termux e Android — Varedura

Guia operacional para instalar, sincronizar, operar e atualizar o **Varedura** nativamente no Android via **Termux** (testado em arquitetura ARM64 / Galaxy M35 5G, Android 16, Python ≥ 3.14).

---

## 1. Visão geral

No Android/Termux, o Varedura executa a mesma **TUI Textual** do desktop diretamente no terminal, com adaptações nativas em [`varedura/termux_env.py`](../varedura/termux_env.py), [`varedura/updater.py`](../varedura/updater.py) e [`rtsp/video.py`](../rtsp/video.py):

- **Sem dependências pesadas de imagem/browser**: não requer Flutter, Pillow, `rich-pixels`, `cairosvg` ou Selenium no aparelho.
- **Detecção automática de ambiente**: `is_termux()` verifica `TERMUX_VERSION`, `PREFIX` (`/data/data/com.termux...`) ou `VAREDURA_TERMUX_MODE=1`; `is_android()` cobre `is_termux()` ou `ANDROID_ROOT`.
- **Telemetria Android em tempo real** (`collect_android_telemetry()` → `AndroidTelemetry`):
  - Bateria (`%`, status e temperatura em °C) via `/sys/class/power_supply/battery/*` com fallback para `termux-battery-status`.
  - Tráfego RX/TX de Wi-Fi (`wlan0`) e dados móveis (`rmnet*`) via `/proc/net/dev`, memória via `/proc/meminfo`, uptime via `/proc/uptime`, IPv4 local e status de root (`su`/`tsu`).
- **Compatibilidade sem root**: o scanner de portas (`monitor/port_scanner.py`), coleta de DNS (`getprop net.dns1`/`net.dns2`) e detecção de gateway (`ip route get 1.1.1.1`, `termux-wifi-connectioninfo`) tratam restrições de permissão do Android graciosamente.

---

## 2. Pré-requisitos e instalação (`scripts/termux_install.sh`)

### Pré-requisitos no Android
1. **Termux** (preferencialmente via F-Droid ou GitHub Releases; evite versões antigas da Play Store).
2. **Termux:API** (aplicativo Android + pacote `termux-api`) para notificações, compartilhamento de relatórios, área de transferência e fallback de bateria/Wi-Fi.
3. **VLC for Android** (`org.videolan.vlc`, opcional) para abrir fluxos RTSP diretamente pelo player nativo.

### O que o instalador faz

O script [`scripts/termux_install.sh`](../scripts/termux_install.sh) é idempotente (shebang `#!/data/data/com.termux/files/usr/bin/bash`, quebras de linha LF) e executa 4 etapas:

1. **Pacotes nativos ARM64 (`apt-get`)**:
   `git`, `python`, `python-psutil`, `matplotlib`, `ffmpeg`, `mpv`, `nmap`, `openssh`, `termux-api`, `termux-tools`, `cronie`.
2. **Pacotes pure-Python (`pip`)**:
   `textual`, `rich`, `requests`, `speedtest-cli`, `reportlab`, `pypdf2`, `truststore`, `idna`, `setuptools`.
3. **Instalação editável do repositório**:
   ```bash
   python3 -m pip install --no-build-isolation --no-deps -e "$REPO_DIR"
   ```
   Por padrão, `$REPO_DIR` resolve para o diretório pai de `scripts/` (ou `~/varedura`).
4. **Substituição opcional do comando `menu` (`--replace-menu`)**:
   - Faz backup de `$PREFIX/bin/menu` em `$PREFIX/bin/menu.m35.bak` **somente se o backup ainda não existir**.
   - Mantém `$PREFIX/bin/m35-center` intacto.
   - Grava `$PREFIX/bin/menu` (`chmod 0755`) com fallback automático para o painel legado:
     ```bash
     #!/data/data/com.termux/files/usr/bin/bash
     shopt -s execfail
     exec varedura "$@" || exec python3 "$HOME/.claro_suite/m35_tui.py" "$@"
     ```

### Execução direta no Termux

```bash
bash ~/varedura/scripts/termux_install.sh
# Ou substituindo o atalho 'menu' mantendo backup em menu.m35.bak:
bash ~/varedura/scripts/termux_install.sh --replace-menu
```

Flags suportadas: `--repo-dir <caminho>`, `--replace-menu`, `--skip-apt`, `-h` / `--help`.

---

## 3. Sincronização do PC via ADB (`scripts/sync_termux_adb.ps1`)

Para enviar o repositório local do Windows para o Termux via USB (sem precisar subir alterações para o GitHub antes de testar), use [`scripts/sync_termux_adb.ps1`](../scripts/sync_termux_adb.ps1).

### Pré-requisitos
- Depuração USB habilitada no aparelho e `adb` acessível no Windows.
- `sshd` em execução no Termux (porta padrão `8022`) e chave pública do PC em `~/.ssh/authorized_keys` para autenticação sem senha (`BatchMode=yes`).

### Exemplos de uso (PowerShell)

```powershell
# Sincronizar apenas os arquivos (auto-detecta o único dispositivo ADB conectado)
.\scripts\sync_termux_adb.ps1

# Sincronizar, instalar dependências/pacote editável e configurar 'menu'
.\scripts\sync_termux_adb.ps1 -Install -ReplaceMenu

# Especificar serial ADB, porta ou diretório remoto diferente
.\scripts\sync_termux_adb.ps1 -Serial RQCX904E6MT -Port 8022 -RemoteDir ~/varedura -Install
```

### Parâmetros e comportamento

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `-Serial` | auto-detectado | Serial ADB (obrigatório apenas se houver mais de 1 aparelho conectado) |
| `-Port` | `8022` | Porta TCP local encaminhada para a porta `8022` do `sshd` no Termux |
| `-RemoteDir` | `~/varedura` | Diretório destino no Termux |
| `-Install` | desligado | Executa `scripts/termux_install.sh` no aparelho após sincronizar |
| `-ReplaceMenu` | desligado | Repassa `--replace-menu` para o instalador (requer `-Install`) |

- **Exclusões automáticas no `tar`**: `.venv`, `.git`, `__pycache__`, `logs`, `exports`, `runtime`, `screenshots`, `graphify-out`, `lmarena`, `build`, `dist`, `*.egg-info`, `.pytest_cache`, `.ruff_cache`, `.coverage`, `.coverage.*`, arquivos privados (`credenciais.json`, `ips_conhecidos.json`, `regioes.json`, `camera_bridge_state.json`, `.camera-locations.private.json`, `roteador_creds.txt`, `router_template.html`) e `todos_ips_belem.txt`.
- **Inicialização segura do Git remoto**: se `<RemoteDir>/.git` ainda não existir no Termux, o script inicializa o repositório na branch `main` e registra `origin = https://github.com/joaosnet/Varedura.git` sem gravar nenhum token no `.git/config`.
- **Armadilha do OpenSSH no Windows PowerShell**: `adb forward tcp:8022 tcp:8022` escuta em IPv4 `127.0.0.1` e o OpenSSH do Windows remove aspas duplas aninhadas e interpreta `>` como redirecionamento dentro de `ssh ... '...'`. Por isso o script força `-4`, usa `127.0.0.1`, desabilita BOM UTF-8 (`[Console]::InputEncoding`) e envia todos os scripts bash em LF-only via `stdin` para `bash -s`.

---

## 4. Autodescoberta de programas e atalhos Termux

Quando em execução no Termux/Android, a aba **Termux** descobre ferramentas locais via `discover_termux_tools()` (`varedura/termux_env.py`) sem modificar nenhum arquivo pessoal:

1. **Ferramentas CLI no `PATH`**:
   `micro`, `btop` (elevado via `sudo env LANG=en_US.UTF-8 TERM=xterm-256color` quando `has_root()` e `sudo` existem), `vernet` / `netscan`, `portscan`, `packetcap`, `vt-status`, `vt-scan` e `painel-web` / `WEB`.
2. **Suíte local (`~/.claro_suite/`)**:
   `claro-monitor`, `claro-audit` e `m35-center` / `~/.claro_suite/m35_tui.py`.
3. **Atalhos Termux:Widget (`~/.shortcuts/` e `~/.shortcuts/tasks/`)**:
   Scripts executáveis não redundantes (ex.: `Alternar_Modo_Banco`), filtrando atalhos que duplicam entradas já descobertas na suíte (`1_Monitor_Claro`, `2_Auditar_ZeroRating`, `3_Scanner_Rede`, `4_Centro_Controle`).
4. **Catálogo customizado (`~/.varedura_termux_tools.json`)**:
   Arquivo opcional contendo uma lista JSON de objetos. Entradas inválidas ou arquivo ausente são ignorados silenciosamente.

### Schema de `~/.varedura_termux_tools.json`

| Campo | Tipo | Obrigatório | Valores / Observações |
|---|---|---|---|
| `id` | `string` | Sim | Identificador único da ferramenta |
| `label` | `string` | Sim | Rótulo exibido na lista da aba Termux |
| `command` | `list[string]` | Sim | Comando e argumentos (ex.: `["nmap", "-sn"]`) |
| `category` | `string` | Não | Categoria de agrupamento (ex.: `"rede"`, `"custom"`) |
| `mode` | `string` | Não | `"suspend"` (ocupa terminal), `"suspend_pause"` (aguarda Enter ao sair), `"background"` ou `"action"` |
| `description` | `string` | Não | Descrição curta exibida ao selecionar |
| `needs_arg` | `bool` | Não | Se `true`, usa o campo de argumento da aba antes de executar |
| `arg_placeholder` | `string` | Não | Texto de dica do argumento (ex.: `"192.168.18.0/24"`) |

Exemplo completo:

```json
[
  {
    "id": "meu-ping-gateway",
    "label": "Ping rápido no gateway",
    "command": ["ping", "-c", "5"],
    "category": "custom",
    "mode": "suspend_pause",
    "description": "Dispara 5 pacotes ICMP para o host informado",
    "needs_arg": true,
    "arg_placeholder": "192.168.18.1"
  },
  {
    "id": "htop-local",
    "label": "Monitor htop",
    "command": ["htop"],
    "category": "sistema",
    "mode": "suspend",
    "description": "Abre o htop ocupando o terminal",
    "needs_arg": false,
    "arg_placeholder": ""
  }
]
```

---

## 5. Reprodução de câmeras IP no Termux (`rtsp/video.py`)

Como o Termux não possui servidor gráfico X11/Wayland por padrão, `rtsp/video.py` adapta a descoberta de players e captura quando `is_android()` é verdadeiro:

1. **VLC Android Intent (`vlc-android`)** — prioridade máxima quando `am` está disponível:
   ```text
   am start -a android.intent.action.VIEW -d <url_rtsp> -p org.videolan.vlc
   ```
2. **`termux-open`** — delega a abertura do stream ao seletor/app padrão do Android.
3. **`mpv` em terminal (`mpv-tct`)** — renderização direta em caracteres/24-bit truecolor no Termux via `comando_mpv_terminal(url)`:
   ```text
   mpv --vo=tct --rtsp-transport=tcp --profile=low-latency <url_rtsp>
   ```
4. **Snapshot JPEG rápido (`capturar_e_abrir_snapshot()`)** — captura um quadro via `ffmpeg` e o abre imediatamente com `termux-open` no visualizador nativo do Android.
5. **Copiar URL RTSP** — botão dedicado na aba Câmeras envia a URL para a área de transferência do Android via `termux-clipboard-set`.

> **Nota técnica**: launchers Android como `am start` e `termux-open` retornam código de saída `0` imediatamente após disparar a Intent no sistema. A função `erro_se_morreu()` trata `returncode == 0` como sucesso, evitando falsos alertas de encerramento prematuro.

---

## 6. Integração com `Termux:API`

As primitivas em `varedura/termux_env.py` conectam a TUI aos recursos nativos do Android sem bloquear o loop assíncrono:

| Recurso | Função / Helper | Comando Termux:API | Uso na TUI |
|---|---|---|---|
| Notificações | `send_termux_notification()` | `termux-notification` | Alertas de queda/recuperação da rede e aviso de atualização Git concluída |
| Compartilhamento | `share_file()` | `termux-share -a send` (fallback `termux-open`) | Envio direto de relatórios CSV e PDF ANATEL para WhatsApp/e-mail/arquivos |
| Abrir alvo | `open_file_or_url()` | `termux-open` | Abertura de arquivos locais ou URLs no Android |
| Clipboard | `copy_to_clipboard()` | `termux-clipboard-set` | Cópia rápida do comando SSH (`ssh -p 8022 ...`) e URLs RTSP |
| Serviços | `list_termux_services()` / `toggle_termux_service()` | `sshd`, `crond`, `termux-wake-lock` / `termux-wake-unlock` | Liga/desliga SSH, cron, wakelock e `claro_daemon` na sub-aba Serviços |

---

## 6.1 Relatórios visíveis no Android

A home do Termux é privada: o gerenciador de arquivos do Android não enxerga `exports/`. Ao concluir uma exportação na aba Rede, `_publish_exports()` (em `cli/textual_app.py`) copia o PDF e os CSVs para **Documentos/Varedura** via `publish_export()` e abre o PDF com `termux-open`. Sem a permissão de armazenamento (`~/storage` ausente), o app dispara `termux-setup-storage` uma vez por sessão, avisa o usuário e ainda assim abre o PDF pelo visualizador do Android. Os originais continuam em `exports/`.

## 7. Teclado, teclas extras e digitação no Termux

Toda TUI com mouse ativo tem três atritos no Termux; o `TermuxKeysMixin` ([`cli/textual_termux_keys.py`](../cli/textual_termux_keys.py)) trata os três:

- **Tecla ⌨ temporária**: com o mouse do terminal ativo, tocar na tela não abre o teclado. Ao iniciar, `set_keyboard_key(True)` acrescenta `{"key": "KEYBOARD"}` no início da última linha da barra `extra-keys` do usuário; ao sair (`on_unmount`, `atexit` e no início da execução seguinte) ela é removida. Só é alterada uma linha `extra-keys = [...]` já existente, em JSON de uma linha; o restante de `~/.termux/termux.properties` fica intacto.
- **Macros das teclas extras**: botões como `{"macro": "
menu
"}` digitam comandos de shell. `extra_key_macros()` lê esses comandos e, dentro da TUI, o LF inicial (que o Textual lê como `ctrl+j`; Enter também vale) é segurado por 150 ms: se o que vem a seguir é um macro conhecido, vira ação do Varedura (`menu` → Painel, `toggle-page` → alternador, `clear` → nada, demais → executa o comando com a TUI suspensa); caso contrário o Enter é reenviado ao widget em foco. Durante a captura nenhum atalho de letra é disparado.
- **Diálogo nativo**: tocar num campo com o teclado fechado abre `termux-dialog text` (Termux:API) com o rótulo do campo; o texto confirmado vai para o campo. O teclado é considerado aberto quando o terminal encolhe para menos de 75 % da maior altura já vista.

### Alternador de botões extra-keys (`F12`)

A TUI mapeia a tecla **`F12`** para `toggle_keyboard_page()`, que invoca `~/.claro_suite/termux_page_switcher.py` (quando presente no dispositivo):

- **Página 1**: barra rápida de ferramentas e atalhos com ícones/emojis configurados no Termux.
- **Página 2**: teclas essenciais de terminal (`CTRL+C`, `clear`, `ESC`, `TAB`, `CTRL`, `UP`/`PGUP`, `DOWN`/`PGDN`).
- Atualiza `~/.termux/termux.properties` e recarrega a barra extra-keys instantaneamente sem reiniciar a sessão.

---

## 8. Visibilidade condicional da aba Docker

Em desktops (Windows, Linux, macOS), a aba **Docker** é sempre exibida. No Android/Termux (`is_android() == True`), `should_show_docker_tab()` oculta a aba **Docker** por padrão quando não há CLI Docker instalada (`has_docker() == False`).

Para exibir a aba manualmente no Android (por exemplo, ao controlar um ambiente com `docker` no `PATH` ou durante testes):

```bash
export VAREDURA_SHOW_DOCKER=1
varedura
```

---

## 9. Atualização automática segura via Git (`varedura-update`)

O módulo [`varedura/updater.py`](../varedura/updater.py) expõe o comando `varedura-update` (e controles equivalentes na aba **Configurações** e na sub-aba **Serviços**) para atualizar o repositório local em `~/varedura` com segurança, inclusive quando o repositório remoto no GitHub for privado.

### Como configurar o token sem expô-lo

`resolve_github_token()` busca o token na seguinte ordem de precedência:
1. Variáveis de ambiente: `GHG_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`.
2. Arquivos locais: `~/.varedura_gh_token` ou `~/.config/varedura/gh_token`.

Modo recomendado no Termux (grava `~/.varedura_gh_token` com permissão `0600`):

```bash
varedura-update --set-token
```

> **Invariante de segurança**: o token **nunca** é gravado em `.git/config`, argumentos de linha de comando ou arquivos de log. As chamadas `git fetch` / `git pull` usam um script temporário `GIT_ASKPASS` (`0700`) que lê o segredo da variável de ambiente efêmera `_VAREDURA_ASKPASS_SECRET`, é removido no bloco `finally` e aplica redação em toda saída capturada.

### Comandos do `varedura-update`

| Comando | Ação |
|---|---|
| `varedura-update --status` | Exibe branch atual, commit curto, se há alterações locais (`dirty`), origem do token e status do cron |
| `varedura-update --check` | Verifica se existem novos commits em `origin/<branch>` respeitando o cooldown de **6h** (`git_last_check` em `~/.varedura_prefs.json`) |
| `varedura-update` | Executa `git pull --ff-only` se o working tree estiver limpo e respeitar o cooldown; se `pyproject.toml` mudou, reinstala em modo editável no Termux e envia `termux-notification` |
| `varedura-update --force` | Ignora o cooldown de 6h (`21600s`) |
| `varedura-update --no-notify` | Suprime a notificação via `Termux:API` |
| `varedura-update --json` | Emite resultado estruturado (`UpdateResult` / status) em JSON |
| `varedura-update --cron-on` | Adiciona ou garante a entrada `0 */6 * * *` marcada com `# VAREDURA-AUTO-UPDATE` no `crontab` do `cronie` preservando outras entradas |
| `varedura-update --cron-off` | Remove somente a entrada `# VAREDURA-AUTO-UPDATE` do `crontab` |
| `varedura-update --repo-dir <dir>` | Aponta para um caminho de repositório específico |

### Proteção contra conflitos locais

Se `git status --porcelain` detectar arquivos modificados localmente, `update_repository()` retorna status `"dirty"` e **não** sobrescreve nem faz merge automático, evitando perda de alterações locais.
