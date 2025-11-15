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

	- `python main.py` — abre uma interface Textual com opções para:
		- Quick Cleanup
		- Full Cleanup
		- Rodar o Models Generator (informe o caminho do arquivo)

		Observações:
		- Quick Cleanup (Subprocess): roda `quick_wsl_cleanup.py` como subprocesso e captura stdout/stderr.
		- Quick Cleanup (In-Process): roda `cli.quick_cleanup.quick_cleanup(console=...)` dentro do processo atual, integrando a saída ao painel de logs.
		- Full Cleanup (Subprocess): roda `wsl_docker_cleaner.py` como subprocesso e captura stdout/stderr.
		- Full Cleanup (Elevado): inicia um novo processo Python elevado (UAC) para executar a limpeza com privilégios de administrador.

	As saídas dos scripts aparecem no painel de logs da interface. Lembre-se: as operações de limpeza são destrutivas e exigem confirmação do usuário.

Estrutura de pastas (modular):

- `docker_cleaner/`: lógica de limpeza e utilitários
- `cli/`: wrappers CLI para executar as ferramentas
- `lmarena/`: utilitários do LMArena (generators)
- `tests/`: testes unitários (pytest)

Riscos: Os scripts executam comandos destrutivos (`docker system prune -af --volumes`, `taskkill`, `wsl --shutdown`, `Optimize-VHD`). Sempre verifique e execute com cautela.

