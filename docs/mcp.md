# Servidor MCP — Varedura

O módulo `mcp_server/` expõe operações centrais do Varedura pelo **Model Context Protocol (MCP)** usando `FastMCP` em transporte `stdio` ([mcp_server/server.py](../mcp_server/server.py)), permitindo que agentes (como GitHub Copilot CLI, VS Code Copilot ou Codex/Claude) consultem métricas e executem manutenções seguras.

---

## 1. Configuração do cliente MCP

Adicione ao `.vscode/mcp.json` do workspace ou ao perfil MCP do seu agente:

```json
{
  "servers": {
    "varedura": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_server"]
    }
  }
}
```

Execução manual direta para depuração:

```powershell
uv run python -m mcp_server
```

---

## 2. Ferramentas expostas

| Ferramenta | Assinatura real | Retorno / Comportamento |
|---|---|---|
| `docker_status` | `docker_status() -> str` | Retorna JSON com `disk_usage` (`docker system df`) e `running_containers` (`docker ps`), ou `{"error": "Docker is not running"}` |
| `docker_quick_cleanup` | `docker_quick_cleanup(confirmed: bool = False, dry_run: bool = False) -> str` | Limpa containers parados, imagens, volumes, redes, sistema e build cache (`WSLDockerCleaner.docker_cleanup`), **preservando containers em execução** |
| `docker_full_cleanup` | `docker_full_cleanup(confirmed: bool = False, dry_run: bool = False) -> str` | Executa `docker_cleanup`, `stop_docker_wsl()` e `compact_vhdx_files()` (Windows exige privilégios de administrador para VHDX) |
| `port_scan` | `port_scan() -> str` | Chama `monitor.port_scanner.run_full_scan()` e retorna totais + até 20 portas TCP listening, até 20 UDP e top processos por conexões |
| `get_logs` | `get_logs(lines: int = 50) -> str` | Lê as últimas `lines` linhas (limitado entre `1` e `500`) do arquivo `*.log` mais recente em `logs/` |

---

## 3. Protocolo de segurança em 2 passos

As ferramentas destrutivas (`docker_quick_cleanup` e `docker_full_cleanup`) possuem **trava dupla obrigatória** no código:

1. **Pré-visualização (`dry_run=True`)**: retorna `"executed": false`, `"dry_run": true` e a lista exata de ações (no `docker_full_cleanup` não toca no Docker; no `docker_quick_cleanup` inclui `current_disk_usage`).
2. **Gate de confirmação (`confirmed=False`, padrão)**: se chamada sem `confirmed=True`, a ferramenta **não executa nada** e devolve `"requires_confirmation": true` com `actions` para o agente pedir autorização explícita ao usuário humano antes de reenviar `confirmed=True`.

Exemplo de fluxo esperado para um agente:
- Usuário: *"Verifique o disco do Docker e faça uma limpeza completa."*
- Agente chama `docker_status()` → depois `docker_full_cleanup(dry_run=True)` → apresenta as ações destrutivas ao usuário → somente após "sim" do usuário chama `docker_full_cleanup(confirmed=True)`.
