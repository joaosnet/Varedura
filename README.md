# Docker Clennear
<p align="center">
  <img src="screenshots/Captura%20de%20tela%202025-11-19%20100122.png" alt="Imagem de destaque do Docker Clennear" />
</p>
Ferramentas para limpeza e compactação de WSL/Docker (Windows) e utilitários para LMArena models

## 🚀 Início Rápido

### Interface Gráfica (Recomendado)

```bash
python main.py
```

**⚠️ IMPORTANTE:** O aplicativo **solicita automaticamente privilégios de administrador** ao iniciar no Windows (via UAC). Isso é necessário para operações como compactação de VHDX e configuração WSL.

**Indicador visual na interface:**
- ✅ **Status: ✓ Admin** (verde) - Privilégios elevados, todas as operações disponíveis
- ⚠️ **Status: ⚠ Sem Admin** (amarelo) - Sem privilégios, algumas operações podem falhar

### CLI (Linha de Comando)

- Limpeza rápida: `python -m cli.quick_cleanup`
- Limpeza completa: `python -m cli.main_cleaner`
- Gerar modelos LMArena: `python -m lmarena.generator lmarena_models.txt`

## 🎨 Interface Textual (TUI)

A interface unificada oferece:

### 📋 Funcionalidades

- **Limpeza Docker Completa** - Executa todas as etapas automaticamente com streaming em tempo real
- **Opções de Limpeza** - Modal com seleção granular de operações:
  - ✅ Parar Docker e WSL
  - ✅ Prune containers (`docker container prune -f`)
  - ✅ Prune images (`docker image prune -af`)
  - ✅ Prune volumes (`docker volume prune -f`)
  - ✅ Prune networks (`docker network prune -f`)
  - ✅ Prune builder cache (`docker builder prune -af`)
  - ✅ Prune system (`docker system prune -af --volumes`)
  - ✅ Configurar sparse (WSL)
  - ✅ Compactar VHDX (requer admin)
  - ✅ Limpar arquivos temporários
- **LMArena Generator** - Processa dumps e gera código Python com lista de modelos
- **Logs em Tempo Real** - Veja a saída dos comandos conforme são executados
- **Persistência de Preferências** - Salva seleções em `~/.docker_clennear_prefs.json`

### 🔥 Streaming em Tempo Real

**NOVIDADE:** Todos os comandos agora exibem saída **linha por linha** em tempo real no `RichLog`:

- ✅ Comandos Docker (prune, system, etc.)
- ✅ Comandos WSL (shutdown, sparse config)
- ✅ PowerShell (Optimize-VHD)
- ✅ LMArena generator (parsing e processamento)

Não há mais espera até o final - você vê cada passo sendo executado!

## 📁 Logs

- **Localização:** `logs/YYYY-MM-DD.log` (rotação diária)
- **Formato:** Texto plano com timestamps UTF-8
- **Conteúdo:** Comandos executados, saídas, erros e tracebacks
- **Acesso:** Botão "Abrir pasta de logs" na interface

### Captura de Erros

O aplicativo captura automaticamente:
- Exceções não tratadas (Python `excepthook`)
- Erros de async workers (`asyncio` exception handler)
- Erros de thread workers (`threading.excepthook`)
- Mensagens de `stderr` (tracebacks, warnings)

## 🏗️ Estrutura do Projeto

```
Docker-Clennear/
├── docker_cleaner/      # Lógica de limpeza e utilitários
│   ├── core.py         # WSLDockerCleaner com métodos sync e async
│   └── __init__.py
├── cli/                # Wrappers CLI
│   ├── main_cleaner.py # Limpeza completa (CLI)
│   ├── quick_cleanup.py # Limpeza rápida (CLI)
│   ├── admin_tasks.py  # Helper para tarefas admin
│   └── richlog.py      # DailyLogWriter para logs rotativos
├── lmarena/            # Utilitários LMArena
│   ├── generator.py    # Gerador de modelos
│   └── __init__.py
├── tests/              # Testes unitários (pytest)
├── logs/               # Logs diários (YYYY-MM-DD.log)
├── main.py             # Interface Textual (TUI)
└── README.md
```

## ⚠️ Avisos de Segurança

**OPERAÇÕES DESTRUTIVAS:** Os scripts executam comandos que **removem dados permanentemente**:

- `docker system prune -af --volumes` - Remove todos containers, imagens, volumes e redes não utilizados
- `taskkill /F` - Força encerramento de processos Docker
- `wsl --shutdown` - Desliga todas as distribuições WSL
- `Optimize-VHD` - Compacta discos virtuais (requer admin)

**Recomendações:**
1. ✅ Faça backup de dados importantes antes de executar
2. ✅ Revise as opções selecionadas no modal antes de confirmar
3. ✅ Execute como administrador para acesso completo às funcionalidades
4. ✅ Monitore os logs em tempo real durante a execução

## 🔧 Requisitos

- **Sistema:** Windows 10/11 com WSL2
- **Python:** 3.8+
- **Docker Desktop:** Instalado e configurado
- **Privilégios:** Administrador (solicitado automaticamente)
- **Dependências:** `rich`, `textual`

## 📖 Documentação Adicional

- [IMPLEMENTACAO_STREAMING.md](IMPLEMENTACAO_STREAMING.md) - Detalhes técnicos do streaming em tempo real

