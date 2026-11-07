# Visual Verification & Authentic Runtime Captures

1. **Zero Placeholders em Demonstrações Visuais**:
   - Nunca usar `dummyimage.com`, blocos de cor sólida artificiais ou placeholders de texto sintéticos quando o usuário solicitar capturas reais do app.
   - Sempre usar feeds fotográficos realistas de câmeras de segurança (RTSP/CCTV reais, vias urbanas, portarias ou garagens em alta resolução).

2. **Captura em Runtime Real (Browser/Simulator Engine)**:
   - Para capturas do aplicativo móvel/web, executar o bundle real (`mobile/build/web` ou emulador) servido via HTTP e capturar via viewport móvel real (ex: Chrome/Playwright em 412x892 ou 390x844).
   - Capturar os estados interativos reais: feed de vídeo ativo, detecções YOLO desenhadas sobre o vídeo, gráficos de ping com dados oscilantes e métricas de host populadas.

3. **Verificação Visual Prévia**:
   - Antes de declarar um entregável visual como "AAA" ou "Real", inspecionar a resolução, renderização de fontes e layout para garantir ausência de artefatos.
