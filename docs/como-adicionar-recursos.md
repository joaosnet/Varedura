# Como Adicionar Recursos — Varedura

Receitas passo a passo para estender cada subsistema sem quebrar os invariantes do projeto (`startup lazy`, i18n sincronizado, mocks em testes e economia de tokens no `graphify`).

---

## 1. Nova etapa de limpeza Docker / WSL2

1. **Backend sync + async (`docker_cleaner/core.py`)**:
   - Se for um comando Docker novo, registre a chave e a tupla `(i18n_key, cmd)` em `DOCKER_CLEANUP_COMMANDS` e, se padrão, em `DEFAULT_DOCKER_CLEANUP_STEPS`.
   - Se for uma etapa de sistema/WSL, implemente o par `def minha_etapa(self) -> bool` e `async def minha_etapa_async(self, stream_callback=None) -> bool` em `WSLDockerCleaner`. Operações que exigem admin devem usar `is_admin()` + `run_elevated_command` / `run_elevated_command_async`.
2. **Metadados e UI compartilhada (`cli/ui_shared.py`)**:
   - Adicione `(key, i18n_key, default_bool)` em `CLEANUP_STEPS`, o peso em `STEP_WEIGHT` e inclua na seção apropriada de `CLEANUP_GROUPS`.
3. **TUI Textual (`cli/textual_app.py`) e traduções (`i18n/`)**:
   - Conecte a nova chave no worker `_run_cleanup_worker` e nas opções da aba `docker` (`_compose_cleanup`).
   - Adicione as mesmas chaves em `i18n/pt.json` e `i18n/en.json`.
4. **Testes**: adicione casos mockando `subprocess` / `ctypes` em `tests/test_docker_cleanup.py`.

---

## 2. Nova aba, modal ou atalho na TUI Textual

1. **Não quebre o startup lazy**: não importe `requests`, `selenium`, `PIL`, `monitor.stalker` ou `rtsp.*` no topo de `cli/textual_app.py` (validado por `tests/test_startup_lazy.py`). Faça imports pesados dentro do worker ou de um helper lazy. Da mesma forma, `varedura/termux_env.py` e `varedura/updater.py` devem permanecer 100% stdlib no topo.
2. **Layout, visibilidade condicional e hidratação (`cli/textual_app.py`)**:
   - Novas abas principais entram em `compose()` com um container `.lazy-pane` e são montadas na primeira ativação em `_hydrate_tab`.
   - Abas dependentes de plataforma (como a aba `docker` controlada por `should_show_docker_tab()`) devem decidir sua visibilidade sem executar subprocessos síncronos pesados na montagem inicial.
   - Modais reutilizáveis (padrão `ModalScreen`) vivem em [cli/network_ui.py](../cli/network_ui.py) e são importados sob demanda.
   - Atalhos globais vão em `BINDINGS` apontando para métodos `action_<nome>()` (incluindo captura nativa de tela SVG).
3. **Workers e UI thread**: use `@work(exclusive=True)` para I/O assíncrono e `@work(thread=True)` para chamadas bloqueantes, atualizando widgets via `self.call_from_thread(...)`.
4. **i18n + Testes**: adicione chaves idênticas em `i18n/{pt,en}.json` (validadas por `tests/test_i18n_parity.py`) e crie testes headless com `async with app.run_test() as pilot:` em `tests/test_textual_app.py`.

---

## 3. Novo alvo de ping, diagnóstico, reparo ou provedor de speedtest

- **Alvo padrão de ping (`monitor/ping_targets.py`)**: adicione entradas no catálogo em `target_catalog()` preservando o `NETWORK_SCHEMA_VERSION = 3` e respeitando `MAX_PERSISTENT_TARGETS = 5`.
- **Novo probe ou causa de falha (`monitor/network_diagnostics.py`)**:
  - Se necessário, adicione enum em `ProbeKind` ou `FailureCause`.
  - Implemente a coleta na interface `ProbeBackend` / `SystemProbeBackend` e mapeie as evidências em `classify_diagnosis`.
- **Novo reparo seguro (`monitor/network_repairs.py`)**:
  - Só torne executável o que for reversível/baixo impacto (adicione em `RepairKind`, monte o `RepairAction` em `list_repair_actions` e execute em `RepairExecutor`). Operações arriscadas devem entrar apenas em `list_repair_guidance` como texto de orientação.
  - Sempre passe pela tela de confirmação `RepairConfirmationScreen` na UI.
- **Score de saúde (`monitor/network_health.py`)**: mantenha `compute_health_score()` puro (sem dependência de Textual/Rich).
- **Novo provedor de speedtest (`monitor/speed_providers.py`, `monitor/speed_tester.py`, `monitor/speed_worker.py`)**:
  - Crie uma subclasse de `SpeedTestProvider` em `monitor/speed_providers.py` implementando `name`, `is_available()`, `run_test()` e `cleanup()`, e registre-a em `MultiProviderSpeedTester`.
  - Registre o novo `provider_id` em `ContinuousSpeedTester._available_provider_ids()` (`monitor/speed_tester.py`) e nos mapas `PROVIDER_IDS` / `factories` de `monitor/speed_worker.py` para que a TUI possa selecioná-lo na rotação de workers.
  - Garanta que importar `monitor.speed_tester` ou chamar `get_speed_tester()` (`monitor/speed_tester.py`) não dispare navegador/rede nem importe `selenium` no startup.
- **Testes**: cubra em `tests/test_ping_targets.py`, `tests/test_network_diagnostics.py`, `tests/test_network_repairs.py`, `tests/test_network_health.py` ou `tests/test_speed_cleanup.py`.

---

## 4. Nova ferramenta no servidor MCP

1. Edite [mcp_server/server.py](../mcp_server/server.py) e adicione uma função decorada com `@mcp.tool()` retornando JSON serializado (`json.dumps(..., indent=2, ensure_ascii=False)`).
2. **Regra de segurança obrigatória**: se a ferramenta alterar estado do sistema ou apagar dados, adicione os parâmetros `confirmed: bool = False, dry_run: bool = False` e reutilize os helpers `_dry_run_preview()` e `_confirmation_required()`.
3. Importe dependências pesadas de runtime (como `monitor.*`) dentro da função quando possível e documente os parâmetros na docstring (o FastMCP expõe a docstring ao cliente).
4. Atualize a tabela de ferramentas em [docs/mcp.md](mcp.md).

---

## 5. Ferramentas Termux, telemetria Android e auto-updater

1. **Descoberta no Termux (`varedura/termux_env.py`)**:
   - Ferramentas nativas entram em `discover_termux_tools()` como `TermuxTool` (respeitando `mode`: `"suspend"`, `"suspend_pause"`, `"background"` ou `"action"`).
   - Usuários finais também podem declarar ferramentas próprias sem alterar código via `~/.varedura_termux_tools.json` (veja o schema em [docs/termux.md](termux.md)).
   - Novos serviços em segundo plano entram em `list_termux_services()` / `toggle_termux_service()`.
2. **Self-updater (`varedura/updater.py`)**:
   - Qualquer interação com Git autenticado deve usar `_run_git_authenticated()` (`GIT_ASKPASS` efêmero via env) e `_redact_token()`, preservando o cooldown de 6h e nunca persistindo tokens em `.git/config`.
3. **Testes**: adicione casos mockando `subprocess`, `/proc`, `/sys` e filesystem em `tests/test_termux_env.py` e `tests/test_updater.py`.

---

## 6. Nova regra de visão AI ou protocolo de câmera

- **Regra espacial AI (`varedura/ai_vision/rules.py`)**: herde de `GeometricRule`, implemente `evaluate(self, camera_id, detections, history) -> list[SpatialEvent]` usando coordenadas normalizadas `[0.0, 1.0]`, e registre via `AIStreamProcessor.add_rule()`. Teste em `tests/test_ai_vision.py`.
- **Protocolo de câmera (`rtsp/camera_engine.py`)**: adicione o esquema em `CameraProtocol`, atualize `parse_camera_url()` e implemente resolução/captura/PTZ em `UnifiedCameraSource`. Nunca logue senhas sem passar por `rtsp/log.py` (`redact_sensitive`).

---

## 7. Checklist final antes de commitar

- [ ] `uv run pytest -q` passando 100% (incluindo `test_startup_lazy.py`, `test_graphify_privacy.py` e `test_i18n_parity.py`).
- [ ] `uv run ruff check .` sem erros nos arquivos modificados.
- [ ] `i18n/pt.json` e `i18n/en.json` com chaves e placeholders sincronizados.
- [ ] `docs/*.md` / `AGENTS.md` atualizados se mudou entrypoint, ferramenta MCP, integração Termux ou dependência.
- [ ] Se alterou `pyproject.toml`, rodou `uv tool upgrade varedura`.
- [ ] Rodou `graphify update .` (e `graphify export wiki` se houve mudança estrutural).
