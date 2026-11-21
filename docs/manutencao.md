# Manutenção — Varedura

Guia operacional para configurar o ambiente local, rodar testes/lint, diagnosticar falhas e manter o grafo de conhecimento (`graphify`) e a documentação em dia.

---

## 1. Ambiente de desenvolvimento (`uv`)

O projeto exige **Python ≥ 3.14.2** e usa **`uv`** como gerenciador canônico no desktop (não use `python` ou `pip` nus).

```powershell
# Instalar/sincronizar dependências de runtime + dev + Selenium (browser-speedtest)
uv sync --dev --extra browser-speedtest

# Instalação global editable para usar `varedura`, `varedura-camera-bridge` e `varedura-update` em qualquer diretório
uv tool install --editable ".[browser-speedtest]"
```

Sempre que alterar `dependencies`, `optional-dependencies` ou `[project.scripts]` em [pyproject.toml](../pyproject.toml), atualize o pacote global:

```powershell
uv tool upgrade varedura
```

> **Nota sobre `[build-system]`**: [pyproject.toml](../pyproject.toml) declara `[build-system]` (`setuptools>=68.0`), portanto `uv sync` gera os entry points (`varedura`, `varedura-camera-bridge`, `varedura-update`) diretamente no `.venv`. Além disso, `[tool.uv]` contém `override-dependencies = ["pywin32>=999; sys_platform == 'win32'"]` para compatibilidade com Python 3.14 free-threaded (`cp314t`).

Para provisionamento e sincronização no **Android / Termux** (ARM64), veja [docs/termux.md](termux.md) e os scripts [scripts/termux_install.sh](../scripts/termux_install.sh) e [scripts/sync_termux_adb.ps1](../scripts/sync_termux_adb.ps1).

---

## 2. Testes e cobertura

A suíte Python em `tests/` isola operações destrutivas (Docker, WSL, `taskkill`, `Optimize-VHD`, UAC, Git/SSH e probes de rede) com mocks:

```powershell
# Suíte completa
uv run pytest -q

# Com cobertura (branch=true configurado em pyproject.toml)
uv run pytest --cov --cov-report=term-missing --cov-report=xml

# Testes críticos de arquitetura, i18n e privacidade
uv run pytest tests/test_startup_lazy.py tests/test_graphify_privacy.py tests/test_i18n_parity.py -q
```

---

## 3. Lint, formatação e CI

O workflow [.github/workflows/ci.yml](../.github/workflows/ci.yml) roda em `ubuntu-latest` e `windows-latest`:

- `uv run ruff check .` — **bloqueante** no CI.
- `uv run ruff format --check .` — **informativo** (`continue-on-error: true`).
- `uv run pytest --cov --cov-report=term-missing --cov-report=xml` — **bloqueante** em Linux e Windows.

Ao editar qualquer módulo, rode `uv run ruff check` nos arquivos modificados antes de finalizar.

---

## 4. Logs e depuração

| Origem | Destino | Observações |
|---|---|---|
| TUI Textual / `DailyLogWriter` | `logs/YYYY-MM-DD.log` | Rotação diária gerida por [cli/richlog.py](../cli/richlog.py); também legível via ferramenta MCP `get_logs(lines=50)` |
| Scanner RTSP (`rtsp/log.py`) | `logs/rtsp.log*` | Aplica `RedactingFilter` / `redact_sensitive` para remover credenciais e URLs `rtsp://` |
| Camera Bridge | `logs/camera_bridge.log*` | Configurável via `--log-file`; também usa `RedactingFormatter` |
| Capturas de tela nativas | `screenshots/*.svg` | Geradas pela captura SVG nativa do Textual |
| Auto-updater (`varedura-update`) | `stdout` / `--json` + `~/.varedura_prefs.json` | Redige tokens via `_redact_token()`; consulte com `varedura-update --status` |

---

## 5. Segurança, privacidade e higiene

1. **Nunca contorne UAC/admin** (`is_admin()` / `run_as_admin()` em `docker_cleaner/core.py` e `monitor/network_repairs.py`).
2. **Proteja tokens GitHub no updater**: nunca grave `GHG_TOKEN`/`GH_TOKEN`/`GITHUB_TOKEN` em `.git/config`, logs ou scripts persistentes; `varedura/updater.py` grava `~/.varedura_gh_token` com permissão `0600` (POSIX) e usa `GIT_ASKPASS` efêmero.
3. **Preserve os guardrails do MCP**: `docker_quick_cleanup` e `docker_full_cleanup` em `mcp_server/server.py` nunca devem executar sem `confirmed=True`.
4. **Não exponha arquivos privados**: os 6 arquivos validados por `tests/test_graphify_privacy.py` (`credenciais.json`, `ips_conhecidos.json`, `regioes.json`, `camera_bridge_state.json`, `.camera-locations.private.json`, `roteador_creds.txt`), além de `router_template.html`, `tests/arp.py` e `tests/router_phishing.py`, estão excluídos no [.gitignore](../.gitignore) e no [.graphifyignore](../.graphifyignore).
5. **Verificação visual autêntica**: nunca use `dummyimage.com` ou placeholders; mantenha quadros CCTV reais em `runtime/cctv_samples/` e valide capturas SVG nativas da TUI em `screenshots/`.

---

## 6. Manutenção do grafo `graphify` (economia de tokens)

O repositório mantém um grafo AST em `graphify-out/` e artigos em `graphify-out/wiki/` para que agentes consultem símbolos sem ler arquivos inteiros:

```powershell
# Após editar código Python (AST-only, sem custo de API)
graphify update .

# Se mover, remover ou adicionar muitos módulos, reconstrua limpo e regenere a wiki:
graphify extract . --code-only --force --allow-dedup-shrink
graphify cluster-only . --no-label --no-viz
graphify export wiki --graph graphify-out/graph.json
graphify benchmark
```

---

## 7. Troubleshooting comum

- **`.venv` inválido (`no Python executable was found`)**: remova `.venv` e recrie com `uv sync --dev --extra browser-speedtest --python 3.14.2`.
- **`varedura-update` não encontrado no PATH**: execute `uv run python -m varedura.updater --status` dentro do repositório ou atualize o pacote global com `uv tool upgrade varedura`.
- **Aba Docker oculta no Android/Termux**: comportamento esperado quando `docker` não está no `PATH` (`should_show_docker_tab()`); defina `VAREDURA_SHOW_DOCKER=1` apenas para teste.
- **Speedtest SIMET / Brasil Banda Larga indisponível**: ambos dependem de `selenium` (extra `browser-speedtest`) + Chrome. Sem eles, `is_available()` retorna `False` e o `MultiProviderSpeedTester` cai para Speedtest.net / Fast.com.
- **Erro `BridgeAlreadyRunning` no `varedura-camera-bridge`**: existe outra instância ativa ou lock órfão `.bridge.lock` em `--output-dir`. Verifique processos `varedura-camera-bridge` / `ffmpeg` antes de remover o lock.
- **Hook do Codex falhando em `graphify`**: confirme que `graphify` está no PATH e que `.codex/hooks.json` chama `graphify hook-check`.
