# CameraBridge

> God node · 52 connections · `varedura/camera_bridge.py`

**Community:** [Community 5](Community_5.md)

## Connections by Relation

### calls
- make_bridge() `EXTRACTED`
- test_shutdown_in_once_mode_skips_all_snapshots() `EXTRACTED`
- [main()](main.md) `EXTRACTED`
- test_runtime_subdirectory_link_is_rejected() `EXTRACTED`

### contains
- camera_bridge.py `EXTRACTED`

### imports
- test_camera_bridge.py `EXTRACTED`

### method
- ._execute_command() `EXTRACTED`
- .run() `EXTRACTED`
- ._session_path() `EXTRACTED`
- ._recover_orphan_sessions() `EXTRACTED`
- .acquire_lock() `EXTRACTED`
- ._write_session() `EXTRACTED`
- ._write_start_failure() `EXTRACTED`
- ._process_command_file() `EXTRACTED`
- ._validate_command() `EXTRACTED`
- ._stop_active() `EXTRACTED`
- .tick() `EXTRACTED`
- .__init__() `EXTRACTED`
- .refresh_inventory() `EXTRACTED`
- ._update_session() `EXTRACTED`
- .write_catalog() `EXTRACTED`
- ._apply_capture() `EXTRACTED`
- ._read_session() `EXTRACTED`
- ._terminate_process() `EXTRACTED`
- ._fail_active() `EXTRACTED`
- .process_commands() `EXTRACTED`
- *…and 20 more `method` connection(s) not listed (lowest-degree first to go)*

### rationale_for
- Loop de coordenação do catálogo, comandos, snapshots e HLS. `EXTRACTED`

### uses
- shutdown_executor() `INFERRED`
- put_command() `INFERRED`
- test_live_lock_rejects_second_bridge() `INFERRED`
- test_set_location_rejects_invalid_or_free_text_payload() `INFERRED`
- test_location_actions_reject_wrong_command_shapes() `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*