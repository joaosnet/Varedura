# Community 51

> 22 nodes · cohesion 0.13

## Key Concepts

- **video.py** (23 connections) — `rtsp/video.py`
- **shutil** (13 connections)
- **abrir_stream()** (8 connections) — `rtsp/video.py`
- **._lancar_player()** (7 connections) — `cli/textual_cameras.py`
- **detectar_player()** (6 connections) — `rtsp/video.py`
- **erro_se_morreu()** (5 connections) — `rtsp/video.py`
- **._abrir_por_chave()** (4 connections) — `cli/textual_cameras.py`
- **._vigia_player()** (4 connections) — `cli/textual_cameras.py`
- **_achar_exe()** (4 connections) — `rtsp/video.py`
- **salvar_snapshot()** (4 connections) — `rtsp/video.py`
- **_ffprobe_disponivel()** (3 connections) — `rtsp/video.py`
- **_montar_comando()** (3 connections) — `rtsp/video.py`
- **._cameras_on_row_selected()** (2 connections) — `cli/textual_cameras.py`
- **_ffplay_disponivel()** (2 connections) — `rtsp/video.py`
- **Popen** (2 connections)
- **Validação e visualização de streams via ffmpeg (ffprobe/ffplay).** (1 connections) — `rtsp/video.py`
- **Abre o stream ao vivo no melhor player disponível. Não bloqueia. Prefere MPC-…** (1 connections) — `rtsp/video.py`
- **Se o player morreu logo após abrir, retorna a última linha de erro. Retorna…** (1 connections) — `rtsp/video.py`
- **Captura um único frame do stream e salva como imagem (precisa de ffmpeg).** (1 connections) — `rtsp/video.py`
- **Procura o executável no PATH e nos locais comuns de instalação.** (1 connections) — `rtsp/video.py`
- **Retorna (familia, caminho_exe) do primeiro player disponível, ou None.** (1 connections) — `rtsp/video.py`
- **Monta a linha de comando específica para cada player.** (1 connections) — `rtsp/video.py`

## Relationships

- [Community 17](Community_17.md) (5 shared connections)
- [Community 15](Community_15.md) (4 shared connections)
- [Community 13](Community_13.md) (4 shared connections)
- [Community 64](Community_64.md) (4 shared connections)
- [Community 0](Community_0.md) (3 shared connections)
- [Community 99](Community_99.md) (3 shared connections)
- [Community 39](Community_39.md) (3 shared connections)
- [Community 34](Community_34.md) (2 shared connections)
- [Community 33](Community_33.md) (1 shared connections)
- [Community 77](Community_77.md) (1 shared connections)
- [Community 26](Community_26.md) (1 shared connections)
- [Community 2](Community_2.md) (1 shared connections)

## Source Files

- `cli/textual_cameras.py`
- `rtsp/video.py`

## Audit Trail

- EXTRACTED: 63 (95%)
- INFERRED: 3 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*