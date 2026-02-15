# 🧹 Varedura

<p align="center">
  <img src="screenshots/Captura de tela 2026-01-14 125838.png" alt="Varedura screenshot" />
</p>

<p align="center">
  <strong>Ferramenta multiplataforma para limpeza de Docker e monitoramento de rede</strong>
</p>

<p align="center">
  <em>"Varedura" — varrer/limpar</em>
</p>

<p align="center">
  <small>Disponível em: <a href="README.md">English</a> • <a href="README.pt-BR.md">Português (pt-BR)</a></small>
</p>

---

## 🚀 Início rápido

### TUI (recomendado)

```bash
# usando uv (recomendado)
uv run main.py

# ou sem uv
python main.py
```

O aplicativo detecta automaticamente o idioma do sistema (Português/Inglês) e solicitará privilégios de administrador quando necessário.

### CLI

```bash
# usando uv (recomendado)
uv run python -m cli.quick_cleanup             # Limpeza rápida do Docker
uv run python -m cli.main_cleaner              # Limpeza completa com barra de progresso
uv run python -m cli.admin_tasks compact_vhdx  # Tarefas que exigem admin (Windows)

# ou execute diretamente com python
python -m cli.quick_cleanup             # Limpeza rápida do Docker
python -m cli.main_cleaner              # Limpeza completa com barra de progresso
python -m cli.admin_tasks compact_vhdx  # Tarefas que exigem admin (Windows)
```

## ✨ Funcionalidades

### 🐳 Limpeza de Docker
- **Prune completo** — containers, imagens, volumes, redes e cache de build
- **Opções granulares** — escolha o que limpar via modal interativo
- **Compactação de VHDX** — recuperação de espaço em discos virtuais WSL2 (Windows)
- **Configuração WSL sparse** — otimiza uso de memória e disco (Windows)
- **Limpeza de arquivos temporários** — remove arquivos em pastas temporárias
- **Transmissão em tempo real** — acompanhe a saída dos comandos linha a linha

### 🔍 Network Stalker
- Monitoramento de rede em tempo real com gráficos de latência
- Scanner de portas e análise de origem de lag
- Exportação de relatórios em PDF com históricos
- Preferências persistentes para exportação

### 📊 Logs & Relatórios
- Logs diários em `logs/YYYY-MM-DD.log`
- Exportação em PDF para relatórios de monitoramento
- Captura automática de exceções (Python, asyncio, threading)

## 🖥️ Multiplataforma

Varedura roda em **Windows**, **Linux** e **macOS**. Recursos específicos de Windows (VHDX, WSL) são ignorados com segurança em outros sistemas.

## 🌍 Internacionalização

Suporte para **Português (pt-BR)** e **English** com detecção automática.

## 🏗️ Estrutura do projeto

(igual ao `README.md` em inglês — consulte para detalhes técnicos e exemplos)

## ⚙️ Instalação

```bash
# Clone
git clone https://github.com/joaosnet/Varedura.git
cd Varedura

# Crie venv & instale
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -e .
```

Usando `uv` (opcional, recomendado para executar tarefas):

```bash
# adicionar dependências (exemplo):
uv add <package>
uv sync

# executar app / testes via uv
uv run main.py
uv run pytest tests/ -v
```

### Requisitos
- **Python** 3.10+
- **Docker** instalado e no PATH
- **Admin/root** para compactação de VHDX e configuração WSL (Windows)
- Dependências: `rich`, `textual`, `psutil`, `matplotlib`, `reportlab`

## ⚠️ Segurança

Operações destrutivas (ex.: `docker system prune -af --volumes`, `Optimize-VHD`) exigem confirmação explícita. Faça backup de dados importantes antes de executar limpezas completas.

## 🧪 Testes

```bash
pytest tests/ -v
```

## 📄 Licença

Consulte o arquivo [LICENSE](LICENSE).

---

<p align="center">
  Construído com ❤️ usando `GitHub Copilot CLI`
</p>