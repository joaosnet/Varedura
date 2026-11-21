# Câmeras IP, Camera Bridge e Visão AI — Varedura

> **Aviso de uso autorizado**: os módulos de descoberta e acesso em `rtsp/` destinam-se exclusivamente à administração de câmeras e redes locais próprias ou devidamente autorizadas pelo proprietário.

Este guia reúne o pacote `rtsp/`, a ponte sanitizada `varedura-camera-bridge` (`varedura/camera_bridge.py`) e o pipeline de análise de vídeo em `varedura/ai_vision/`.

---

## 1. Subsistema `rtsp/` (descoberta, protocolos e players)

Todos os módulos usam `rtsp.DATA_DIR` (raiz do repositório) para resolver os arquivos locais gitignored (`credenciais.json`, `ips_conhecidos.json`, `regioes.json`).

| Módulo | Papel | Símbolos-chave |
|---|---|---|
| `rtsp/camera_engine.py` | Abstração unificada para `rtsp://`, `icsee://`, `p2p://`, `onvif://` e `http://` | `CameraProtocol`, `CameraMetadata`, `UnifiedCameraSource`, `CameraFleetManager`, `parse_camera_url` |
| `rtsp/xiongmai.py` | Codec binário proprietário Xiongmai NetIP (TCP/UDP porta `34567`) e travessia Sofia Cloud P2P (PTZ, áudio, snapshot, keepalive) | `XiongmaiNetIPClient`, `XiongmaiDiscovery`, `SofiaP2PClient`, `NetIPPacket`, `PTZCommand` |
| `rtsp/scanner.py` | Probe stdlib de portas comuns (`554`, `8554`, `80`, `8080`, `88`, `8000`, `37777`, `34567`), DESCRIBE RTSP e varredura paralela | `ResultadoRTSP`, `testar_porta`, `escanear_portas_camera`, `testar_rtsp`, `escanear_rede` |
| `rtsp/video.py` | Descoberta de stream por lista de caminhos, validação via `ffprobe`/`ffmpeg` e disparo de player (`ffplay`/`vlc`/`mpv`) | `InfoStream`, `detectar_player`, `validar_stream`, `descobrir_stream`, `abrir_stream`, `salvar_snapshot` |
| `rtsp/paths.py` | Catálogo ordenado de caminhos RTSP por fabricante (Genérico, ONVIF, Hikvision, Dahua, Intelbras, etc.) | `CAMINHOS_RTSP`, `caminhos` |
| `rtsp/credenciais.py` | Vault local (`credenciais.json`) e cache de combinações bem-sucedidas (`ips_conhecidos.json`) | `Par`, `CredencialIP`, `carregar_vault`, `carregar_conhecidos`, `combinar_credenciais` |
| `rtsp/regioes.py` & `rtsp/rede.py` | Regiões/câmeras fixas (`regioes.json`) e detecção automática das sub-redes locais | `Regiao`, `carregar_regioes`, `RedeLocal`, `detectar_redes` |
| `rtsp/geo.py` & `rtsp/mapa.py` | Geolocalização e mapa ASCII com pinos para visualização na TUI | `Geo`, `geolocalizar`, `Pino`, `render` |
| `rtsp/log.py` | Logger rotacionado em `logs/rtsp.log` com redação obrigatória de credenciais e URLs RTSP | `redact_sensitive`, `RedactingFilter`, `configurar`, `obter_logger` |
| `rtsp/amostra_ips_belem.py` | Utilitário auxiliar de amostragem de prefixos regionais (gera `todos_ips_belem.txt`; este último deve permanecer preservado e excluído do `graphify`) | `buscar_prefixos_por_asn`, `obter_amostra_aleatoria` |

---

## 2. Ponte local sanitizada (`varedura-camera-bridge`)

O executável `varedura-camera-bridge` ([varedura/camera_bridge.py](../varedura/camera_bridge.py)) conecta o inventário privado de câmeras do Varedura a clientes visuais locais (como o *Mural dos Sonhos*) sem nunca vazar IPs privados, credenciais ou URLs RTSP.

### Fronteira de segurança e layout de `--output-dir`

```
camera_bridge_state.json / dados privados (lidos só pela ponte)
        │
        ▼
  CameraBridge (lock .bridge.lock + FFmpegRunner + LocationStore + IdentityStore)
        │
        ├── catalog.json                  (IDs opacos, nomes sanitizados, capabilities)
        ├── .camera-locations.private.json (localização manual/device gravada via LocationStore dentro de --output-dir)
        ├── heartbeat.json / bridge.pid   (saúde do processo)
        ├── snapshots/<camId>.jpg         (captura periódica via FFmpeg)
        ├── sessions/<sessionId>/         (playlists/segmentos HLS sob demanda, lease TTL)
        └── commands/
              ├── inbox/                  (JSON assinado por schema: refresh|start|heartbeat|stop|shutdown|set_location|clear_location)
              ├── processing/
              └── outbox/                 (acks e erros sanitizados)
```

### Uso via CLI

```powershell
varedura-camera-bridge --output-dir "C:\caminho\para\runtime\cameras"
```

Flags suportadas (`build_parser()`): `--output-dir` (obrigatório), `--log-file`, `--poll-interval` (padrão `1.0s`), `--snapshot-interval` (padrão `30.0s`), `--session-ttl` (padrão `45.0s`) e `--once`.

### Índice de faixas de linha: `varedura/camera_bridge.py` (1.862 linhas)
- `L39-90`: constantes (`SCHEMA_VERSION`, `DEFAULT_*`, `_ALLOWED_ACTIONS`, `_COMMAND_KEYS`, `_LOCATION_KEYS`)
- `L95-285`: helpers de tempo, UUID, escrita JSON atômica, sanitização de URL RTSP (`_rtsp_without_auth`, `_safe_display_name`)
- `L289-637`: `CameraLocation`, `LocationStore`, `CameraSource`, `IdentityStore`, `load_private_inventory()`
- `L641-811`: `CaptureResult`, `HlsProcess`, `FFmpegRunner` (`capture_snapshot`, `start_hls`)
- `L814-1095`: `BridgeAlreadyRunning`, `ActiveSession`, `CameraBridge.__init__`, lock PID/instância, inventário e escrita de `catalog.json`
- `L1097-1456`: captura assíncrona de snapshots, gerenciamento de sessões HLS, recuperação de processos órfãos e `outbox`
- `L1459-1775`: validação estrita de comandos (`_validate_command`), execução (`_execute_command`), `tick()` e `run()`
- `L1778-1858`: `build_parser()`, `configure_logging()` e `main()`

---

## 3. Pipeline de Visão AI (`varedura/ai_vision/`)

| Módulo | Responsabilidade | Símbolos-chave |
|---|---|---|
| `varedura/ai_vision/detector.py` | Inferência YOLOv8/v11 nano via `onnxruntime` (com fallback seguro sem ONNX), `nms()`, `compute_iou()` e tracker guloso por IoU | `Detection`, `ObjectDetector`, `YOLONanoDetector`, `COCO_CLASSES`, `compute_iou`, `nms` |
| `varedura/ai_vision/rules.py` | Regras geométricas sobre coordenadas normalizadas `[0.0, 1.0]` e acumulador de densidade espacial 32×32 | `GeometricRule`, `LineCrossingRule` (tripwire), `ZoneIntrusionRule` (polígono + dwell), `LoiteringRule`, `MotionHeatmap`, `SpatialEvent`, `EventSeverity` |
| `varedura/ai_vision/stream_processor.py` | Orquestrador por câmera com rate limit (`max_fps`), histórico de trajetórias, pre-buffer de frames, avaliação de regras e callbacks | `VideoFrame`, `AIStreamProcessor` (`add_rule`, `process_frame`, `get_status_summary`) |
