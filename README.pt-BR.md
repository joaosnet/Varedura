# 🧹 Varedura

<p align="center">
  <img src="screenshots/demo.gif" alt="Varedura demo" width="720" />
</p>

<p align="center">
  <strong>Ferramenta multiplataforma de limpeza Docker, monitor de rede & servidor MCP — construído inteiramente com GitHub Copilot CLI</strong>
</p>

<p align="center">
  <em>"Varedura" — varrer / limpar</em>
</p>

<p align="center">
  <a href="https://github.com/joaosnet/Varedura/blob/main/LICENSE"><img src="https://img.shields.io/badge/licença-MIT-blue.svg" alt="MIT License" /></a>
  <a href="https://github.com/joaosnet/Varedura"><img src="https://img.shields.io/badge/python-≥3.14-3776AB.svg?logo=python&logoColor=white" alt="Python 3.14+" /></a>
  <a href="https://github.com/joaosnet/Varedura"><img src="https://img.shields.io/badge/plataforma-Windows%20|%20Linux%20|%20macOS-lightgrey.svg" alt="Plataforma" /></a>
  <a href="https://dev.to/challenges/github-2026-01-21"><img src="https://img.shields.io/badge/DEV-GitHub%20Copilot%20CLI%20Challenge-black?logo=dev.to" alt="DEV Challenge" /></a>
</p>

<p align="center">
  <sub>Disponível em: <a href="README.md">English</a> · <a href="README.pt-BR.md">Português (pt-BR)</a></sub>
</p>

<p align="center">
  <a href="#-instalação-rápida">Instalar</a> ·
  <a href="#-funcionalidades">Funcionalidades</a> ·
  <a href="#-servidor-mcp--integração-copilot-cli">MCP + Copilot</a> ·
  <a href="#%EF%B8%8F-multiplataforma">Multiplataforma</a> ·
  <a href="#-construído-com-github-copilot-cli">Copilot CLI</a>
</p>

---

## 📦 Instalação Rápida

### Uma linha (recomendado)

**Windows** (PowerShell):
```powershell
irm https://raw.githubusercontent.com/joaosnet/Varedura/main/install.ps1 | iex
```

**Linux / macOS**:
```bash
curl -fsSL https://raw.githubusercontent.com/joaosnet/Varedura/main/install.sh | bash
```

Após instalar, digite **`varedura`** em qualquer terminal para iniciar.

> O instalador detecta automaticamente o sistema operacional, verifica ferramentas necessárias (`uv`, `Docker`, `Git`), instala apenas o que falta, e suporta **Português** e **Inglês**. Se o Varedura já estiver instalado, oferece opções de **reinstalar** ou **desinstalar**.

### Outros métodos de instalação

<details>
<summary><strong>Instalar com uv (manual)</strong></summary>

```bash
uv tool install git+https://github.com/joaosnet/Varedura.git --python ">=3.14"
```

Depois execute: `varedura`

</details>

<details>
<summary><strong>Clonar e executar do código-fonte</strong></summary>

```bash
git clone https://github.com/joaosnet/Varedura.git
cd Varedura
uv run main.py           # TUI (recomendado)
```

</details>

<details>
<summary><strong>Módulos CLI (sem TUI)</strong></summary>

```bash
uv run python -m cli.quick_cleanup             # Limpeza rápida do Docker
uv run python -m cli.main_cleaner              # Limpeza completa com barra de progresso
uv run python -m cli.admin_tasks compact_vhdx  # Tarefas admin (Windows)
```

</details>

<details>
<summary><strong>Desinstalar</strong></summary>

**Via instalador:**
```powershell
# Windows
.\install.ps1 -Uninstall
```
```bash
# Linux / macOS
./install.sh --uninstall
```

**Ou via uv:**
```bash
uv tool uninstall varedura
```

</details>

### Requisitos

| Requisito | Notas |
|---|---|
| **Python ≥ 3.14.2** | Gerenciado automaticamente pelo `uv` durante a instalação |
| **uv** | Instalado automaticamente pelo instalador se ausente |
| **Docker** | Opcional — necessário para funcionalidades de limpeza Docker |
| **Admin / root** | Opcional — necessário para compactação VHDX e config WSL (Windows) |

---

## 📌 Estado Atual do Projeto

Atualmente, o Varedura é um app de terminal baseado em **Rich**, com módulos separados para limpeza Docker, diagnóstico de rede, integração MCP e gravação de sessão.

- Interface principal: menu animado em `main.py` (sem Textual)
- Limpeza Docker: lógica sync + async em `docker_cleaner/core.py`
- Ferramentas de rede: `monitor/stalker.py`, `monitor/port_scanner.py`, `monitor/speed_tester.py`
- Servidor MCP: `mcp_server/server.py` (5 ferramentas para agentes de IA)
- Gravador de sessão: captura SVG + geração de GIF em `recorder/`
- i18n: suporte bilíngue em `i18n/en.json` e `i18n/pt.json`
- Utilitário de modelos: parser/gerador LM Arena em `lmarena/`

---

## ✨ Funcionalidades

### 🐳 Limpeza de Docker
- **Prune completo** — containers, imagens, volumes, redes e cache de build
- **Opções granulares** — escolha o que limpar via menu interativo
- **Compactação de VHDX** — recuperação de espaço em discos virtuais WSL2 (Windows)
- **Configuração WSL sparse** — otimiza uso de memória e disco (Windows)
- **Limpeza de arquivos temporários** — remove arquivos em pastas temporárias
- **Transmissão em tempo real** — acompanhe a saída dos comandos linha a linha

### 🔍 Network Stalker
- Monitoramento de rede em tempo real com gráficos de latência
- Scanner de portas com identificação de processos
- Teste de velocidade de internet (multi-provedor: Speedtest.net, Fast.com)
- Verificação de conformidade ANATEL (regulação de banda larga brasileira)
- Exportação de relatórios em PDF com históricos
- Preferências persistentes para exportação

### 🤖 Servidor MCP (Integração com IA)
- Expõe ferramentas do Varedura para o **GitHub Copilot CLI** e outros agentes via [Model Context Protocol](https://modelcontextprotocol.io/)
- 5 ferramentas disponíveis: `docker_status`, `docker_quick_cleanup`, `docker_full_cleanup`, `port_scan`, `get_logs`
- Configuração automática do `.vscode/mcp.json` pelo menu de Configurações
- Funciona perfeitamente com o modo agente do GitHub Copilot CLI

### 🎬 Gravador de Sessão
- Gravação automática de GIF das sessões de terminal
- Captura de snapshots SVG → geração de GIF animado
- Atualiza automaticamente `screenshots/demo.gif` para o README
- Liga/desliga pelo menu de Configurações

### 🤖 Mascote Animado
- Robô pixel-art com animações baseadas em estado
- Estados: Idle, Working, Success, Error, Scanning, Wave
- Balões de fala com mensagens contextuais

### 📊 Logs & Relatórios
- Logs diários em `logs/YYYY-MM-DD.log`
- Exportação em PDF para relatórios de monitoramento
- Exportação CSV de histórico de ping e velocidade
- Captura automática de exceções (Python, asyncio, threading)

### 🌍 Internacionalização
- **Detecta automaticamente** o idioma do sistema (Português / Inglês)
- **Troque a qualquer momento** pelo menu de Configurações
- **350+ chaves de tradução** cobrindo toda a interface
- **Persiste** a escolha em `~/.varedura_lang.json`

### 🧠 Modelos LM Arena
- Faz parsing e normalização de listas de modelos para fluxos LM Arena
- Gera saídas estruturadas a partir de `lmarena/lmarena_models.txt`

---

## 🤖 Servidor MCP & Integração Copilot CLI

O Varedura inclui um **servidor MCP (Model Context Protocol)** que expõe suas ferramentas para agentes de IA como o **GitHub Copilot CLI**.

### Configuração

No menu do Varedura, vá em **Configurações → Servidor MCP** para configurar automaticamente, ou adicione manualmente em `.vscode/mcp.json`:

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

### Ferramentas MCP Disponíveis

| Ferramenta | Descrição |
|------------|-----------|
| `docker_status` | Uso de disco Docker, containers rodando, contagem de imagens/volumes |
| `docker_quick_cleanup` | Prune de containers, imagens, volumes, redes e build cache |
| `docker_full_cleanup` | Limpeza completa + shutdown WSL + compactação VHDX (Windows) |
| `port_scan` | Escaneamento de portas TCP/UDP, top processos por conexões |
| `get_logs` | Recuperar entradas recentes do log (até 500 linhas) |

### Uso com Copilot CLI

Uma vez configurado, o GitHub Copilot CLI pode usar as ferramentas diretamente:

```
> Quanto espaço Docker estou usando?             → chama docker_status
> Limpar todos os recursos Docker não usados     → chama docker_quick_cleanup
> Quais portas estão escutando no meu sistema?   → chama port_scan
> Mostrar as últimas 50 entradas do log          → chama get_logs
```

---

## 🖥️ Multiplataforma

Varedura roda em **Windows**, **Linux** e **macOS**:

| Funcionalidade | Windows | Linux | macOS |
|----------------|---------|-------|-------|
| Docker prune/limpeza | ✅ | ✅ | ✅ |
| Parar processos Docker | ✅ `taskkill` | ✅ `systemctl`/`killall` | ✅ `killall`/`open` |
| Compactação VHDX | ✅ `Optimize-VHD` | ⬜ N/A | ⬜ N/A |
| Config WSL sparse | ✅ | ⬜ N/A | ⬜ N/A |
| Limpeza de temp | ✅ `%TEMP%` | ✅ `/tmp` | ✅ `/tmp` |
| Limpeza da lixeira | ✅ PowerShell | ⬜ Ignorado | ⬜ Ignorado |
| Elevação admin | ✅ UAC | ✅ `sudo` | ✅ `sudo` |
| Network Stalker | ✅ | ✅ | ✅ |
| Servidor MCP | ✅ | ✅ | ✅ |
| Instalação one-liner | ✅ `irm \| iex` | ✅ `curl \| bash` | ✅ `curl \| bash` |

> Recursos exclusivos do Windows (VHDX, WSL sparse) são ignorados com segurança em outras plataformas com uma mensagem informativa.

---

## 🏗️ File Tree Atual (Mar 2026)

```
Varedura/
├── .github/
├── .vscode/
├── build/
│   └── lib/
│       ├── cli/
│       ├── docker_cleaner/
│       ├── i18n/
│       ├── mascot/
│       ├── mcp_server/
│       ├── monitor/
│       └── recorder/
├── cli/
│   ├── admin_tasks.py
│   ├── main_cleaner.py
│   ├── quick_cleanup.py
│   └── richlog.py
├── docker_cleaner/
│   └── core.py
├── exports/
├── i18n/
│   ├── en.json
│   └── pt.json
├── lmarena/
│   ├── generator.py
│   ├── lmarena_models.txt
│   └── models.py
├── mascot/
│   ├── frames.py
│   ├── generate_sprites.py
│   ├── images/
│   └── renderer.py
├── mcp_server/
│   ├── __main__.py
│   └── server.py
├── monitor/
│   ├── port_scanner.py
│   ├── speed_providers.py
│   ├── speed_tester.py
│   └── stalker.py
├── recorder/
│   ├── gif_generator.py
│   └── session_recorder.py
├── recordings/
├── screenshots/
├── tests/
│   ├── images/
│   ├── static/
│   ├── test_export_pdf.py
│   ├── test_export_prefs.py
│   └── test_export_prompt.py
├── install.ps1
├── install.sh
├── LICENSE
├── main.py
├── POST-SUBMISSION.md
├── pyproject.toml
├── README.md
├── README.pt-BR.md
├── router_template.html
└── uv.lock
```

---

## ⚠️ Segurança

**Operações destrutivas** sempre requerem confirmação explícita do usuário:

| Comando | Efeito |
|---------|--------|
| `docker system prune -af --volumes` | Remove TODOS os containers, imagens, volumes e redes não usados |
| `taskkill /F` / `killall` | Mata processos Docker à força |
| `wsl --shutdown` | Para todas as distribuições WSL (Windows) |
| `Optimize-VHD` | Compacta arquivos VHDX (Windows, requer admin) |

**Recomendações:**
1. ✅ Faça backup de dados importantes antes de executar limpeza
2. ✅ Revise as opções selecionadas antes de confirmar
3. ✅ Execute como admin/root para funcionalidade completa
4. ✅ Monitore os logs em tempo real durante a execução

---

## 🧪 Testes

```bash
uv run python -m pytest tests/ -v
```

Todas as operações destrutivas são mockadas nos testes — nenhum comando Docker é executado de verdade.

---

## 🤖 Construído com GitHub Copilot CLI

> *Este projeto foi construído para o [GitHub Copilot CLI Challenge](https://dev.to/challenges/github-2026-01-21).*

**Todas as funcionalidades** do Varedura foram desenvolvidas usando [GitHub Copilot CLI](https://github.com/features/copilot/cli) como ferramenta principal de desenvolvimento — desde decisões de arquitetura até implementação, debugging e testes.

Como o Copilot CLI foi usado ao longo do projeto:

- **🏗️ Arquitetura** — Projetou o modelo de execução dual sync/async, integração MCP e abstração cross-platform
- **🐳 Docker Cleaner** — Implementou WSLDockerCleaner com streaming de saída, elevação admin e compactação VHDX
- **🔍 Monitor de Rede** — Construiu o stalker, scanner de portas e speed tester com suporte multi-provedor
- **🤖 Servidor MCP** — Criou o servidor Model Context Protocol expondo todas as ferramentas para agentes IA
- **🎨 TUI & Mascote** — Projetou o sistema de menus Rich e o mascote robô pixel-art animado
- **🌍 Sistema i18n** — Implementou 350+ chaves de tradução bilíngues com auto-detecção
- **📦 Instalador** — Criou os scripts de instalação standalone (install.sh + install.ps1) seguindo padrões UV/OpenClaw
- **🎬 Gravador de Sessão** — Construiu o pipeline de gravação SVG→GIF para geração automática de demos
- **🧪 Testes** — Escreveu testes unitários com mocking adequado para todas as operações destrutivas

---

## 📄 Licença

MIT — consulte [LICENSE](LICENSE) para detalhes.

---

<p align="center">
  Construído com ❤️ usando <a href="https://github.com/features/copilot/cli">GitHub Copilot CLI</a>
</p>