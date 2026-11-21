# Copilot Instructions — Varedura

As instruções canônicas, mapa de módulos, tabela "Onde mudar X", invariantes e regras de economia de tokens deste repositório ficam em [`AGENTS.md`](../AGENTS.md). Leia [`AGENTS.md`](../AGENTS.md) primeiro e consulte `docs/` sob demanda.

- Use sempre `uv` (`uv run pytest -q`, `uv run ruff check .`, `uv run main.py`) — nunca `python` ou `pip` nus.
- Antes de abrir arquivos brutos, consulte o grafo (`graphify query "<pergunta>" --budget 800`) ou `graphify-out/wiki/index.md`.
