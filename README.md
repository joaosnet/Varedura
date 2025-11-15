# Docker Clennear
Ferramentas para limpeza e compactação de WSL/Docker (Windows) e utilitários para LMArena models

Como usar (exemplos):

- Executar limpador principal (com UI):
	- `python wsl_docker_cleaner.py` (compat wrapper que chama `docker_cleaner.core`)
	- ou `python -m cli.main_cleaner`
- Executar limpeza rápida:
	- `python quick_wsl_cleanup.py`
	- ou `python -m cli.quick_cleanup`
- Gerar modelos a partir de dump LMArena:
	- `python models_generator.py lmarena_models.txt`
	- ou `python -m lmarena.generator lmarena_models.txt`

	## UI Centralizada (Textual)

	Também é possível iniciar uma interface TUI que unifica as ferramentas do projeto:

		- `python main.py` — abre uma interface Textual com uma única ação de limpeza ("Limpeza Docker") que abre um modal
			com opções selecionáveis para executar as ações desejadas. As opções incluem:
				- Parar Docker e WSL
				- Prune containers (docker container prune -f)
				- Prune images (docker image prune -af)
				- Prune volumes (docker volume prune -f)
				- Prune networks (docker network prune -f)
				- Prune builder cache (docker builder prune -af)
				- Prune system (docker system prune -af --volumes)
				- Configurar sparse (WSL)
				- Botões de ação no modal: "Executar", "Salvar" (persiste preferência) e "Sair" (fecha o app)
				- As preferências salvas vão para: `~/.docker_clennear_prefs.json` (JSON com booleanos por checkbox id)
				- Parar Docker e WSL
				- Configurar sparse (WSL)
				- Add the new admin helper for tasks that require elevation
				- Admin helper: `python -m cli.admin_tasks compact_vhdx` (or `configure_sparse`) can be used to run admin-only tasks without relaunching the full UI. The UI may use UAC to launch this helper when required.

		Observações:
		- As operações são granulares: selecione individualmente os prunes e as ações que você deseja executar.
		- `quick_wsl_cleanup.py` e `wsl_docker_cleaner.py` ainda existem como helpers CLI, mas a UI agora foca em ações granulares para maior controle.
		- Parar Docker e WSL: executa `taskkill`/`wsl --shutdown` para finalizar serviços antes de limpar.
		- Configurar sparse (WSL): escreve um `.wslconfig` e aplica opção `--set-sparse` em distribuições de docker.
		- Compactar VHDX: chama `Optimize-VHD` via PowerShell (requer privilégios administrativos).
		- Limpar arquivos temporários: remove arquivos temporários e logs do Docker no sistema.

	As saídas dos scripts aparecem no painel de logs da interface. Lembre-se: as operações de limpeza são destrutivas e exigem confirmação do usuário.

	Logs
	----
	O TUI grava logs localmente em `logs/YYYY-MM-DD.log`. Use o botão "Abrir pasta de logs" na interface para abrir a pasta `logs` no explorador/gestor de arquivos. Logs com formatação rich são mostrados na UI com `RichLog`, e preservados em arquivo no formato texto com timestamps.

	Captura de erros e tracebacks
	----------------------------
	O aplicativo redireciona `stderr` e configura o logger do Python para que exceções não tratadas, `tracebacks` e erros de workers (thread/async) sejam capturados no arquivo de log diário. Isso inclui erros levantados por background workers e mensagens impressas para `stderr`.

Estrutura de pastas (modular):

- `docker_cleaner/`: lógica de limpeza e utilitários
- `cli/`: wrappers CLI para executar as ferramentas
- `lmarena/`: utilitários do LMArena (generators)
- `tests/`: testes unitários (pytest)

Riscos: Os scripts executam comandos destrutivos (`docker system prune -af --volumes`, `taskkill`, `wsl --shutdown`, `Optimize-VHD`). Sempre verifique e execute com cautela.

