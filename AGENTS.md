Sempre pesquise na documentação usando mcp e se necessario depois na internet antes usar qualquer biblioteca externa.

## Environment / running the app

- The project is installed as a **global uv tool in editable mode**: `uv tool install --editable ".[browser-speedtest]"`. The `varedura` command (at `C:\Users\joaod\.local\bin\varedura.exe`) launches the TUI from anywhere and reflects source changes immediately (editable install).
- Because of this, **whenever dependencies change in pyproject.toml** (`uv add`, edits to `dependencies`/extras), also run `uv tool upgrade varedura` so the global tool environment picks them up. Code-only changes need nothing.
- The `browser-speedtest` extra (selenium) is intentionally included in the tool install — do not reinstall without it.
- Inside the repo, `uv run main.py` / `uv run pytest` remain the canonical dev commands; never use bare `python`/`pip`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Visual Verification & Authentic Runtime Captures
1. **Zero Placeholders em Demonstrações Visuais**:
   - Nunca usar `dummyimage.com`, blocos de cor sólida artificiais ou placeholders de texto sintéticos quando o usuário solicitar capturas reais do app.
   - Sempre usar feeds fotográficos realistas de câmeras de segurança (RTSP/CCTV reais, vias urbanas, portarias ou garagens em alta resolução).
2. **Captura em Runtime Real (Browser/Simulator Engine)**:
   - Para capturas do aplicativo móvel/web, executar o bundle real (`mobile/build/web` ou emulador) servido via HTTP e capturar via viewport móvel real (ex: Chrome/Playwright em 412x892 ou 390x844).
   - Capturar os estados interativos reais: feed de vídeo ativo, detecções YOLO desenhadas sobre o vídeo, gráficos de ping com dados oscilantes e métricas de host populadas.
3. **Verificação Visual Prévia**:
   - Antes de declarar um entregável visual como "AAA" ou "Real", inspecionar a resolução, renderização de fontes e layout para garantir ausência de artefatos.
