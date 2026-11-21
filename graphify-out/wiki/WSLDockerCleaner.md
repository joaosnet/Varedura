# WSLDockerCleaner

> God node · 78 connections · `docker_cleaner/core.py`

**Community:** [Community 7](Community_7.md)

## Connections by Relation

### calls
- quick_cleanup() `EXTRACTED`
- run_cleanup_steps() `EXTRACTED`
- [main()](main.md) `EXTRACTED`
- run_docker_cleanup() `EXTRACTED`
- .do_GET() `EXTRACTED`
- [main()](main.md) `EXTRACTED`
- test_compact_vhdx_files_requests_elevation_and_falls_back() `EXTRACTED`
- test_compact_vhdx_reports_failure_when_diskpart_fails_without_optimize_vhd() `EXTRACTED`
- test_configure_wsl_sparse_elevates_manage_commands() `EXTRACTED`
- test_configure_wsl_sparse_skips_missing_docker_distros_and_keeps_config() `EXTRACTED`
- test_configure_wsl_sparse_warns_but_does_not_fail_when_manage_fails() `EXTRACTED`
- .run_docker_cleanup() `EXTRACTED`
- test_container_step_only_prunes_stopped_containers() `EXTRACTED`
- test_image_step_does_not_stop_containers_before_prune() `EXTRACTED`
- test_docker_cleanup_preserves_running_containers() `EXTRACTED`
- test_parse_wsl_distros_drops_shell_metacharacters() `EXTRACTED`
- test_stop_docker_wsl_uses_elevated_batch_without_process_errors() `EXTRACTED`
- test_windows_elevated_command_uses_temp_files_not_start_process_redirects() `EXTRACTED`

### contains
- core.py `EXTRACTED`

### imports
- legacy_app.py `EXTRACTED`
- ui_shared.py `EXTRACTED`
- daemon_api.py `EXTRACTED`
- test_docker_cleanup.py `EXTRACTED`
- server.py `EXTRACTED`
- quick_cleanup.py `EXTRACTED`
- admin_tasks.py `EXTRACTED`

### method
- .compact_vhdx_files() `EXTRACTED`
- .log() `EXTRACTED`
- .compact_vhdx_files_async() `EXTRACTED`
- .run_command() `EXTRACTED`
- .run_command_async() `EXTRACTED`
- .docker_cleanup() `EXTRACTED`
- .configure_wsl_sparse() `EXTRACTED`
- .run_full_cleanup_with_progress() `EXTRACTED`
- .run_elevated_command() `EXTRACTED`
- .stop_docker_wsl() `EXTRACTED`
- .run_elevated_command_async() `EXTRACTED`
- .is_admin() `EXTRACTED`
- .docker_cleanup_async() `EXTRACTED`
- .configure_wsl_sparse_async() `EXTRACTED`
- ._run_docker_cleanup_step() `EXTRACTED`
- ._docker_wsl_sparse_distros() `EXTRACTED`
- ._build_windows_elevated_command() `EXTRACTED`
- .get_docker_vhdx_size() `EXTRACTED`
- ._ensure_wsl_distros_running() `EXTRACTED`
- ._fstrim_wsl_distros() `EXTRACTED`
- *…and 27 more `method` connection(s) not listed (lowest-degree first to go)*

### uses
- DailyLogWriter `INFERRED`
- docker_quick_cleanup() `INFERRED`
- docker_full_cleanup() `INFERRED`
- VareduraDaemonState `INFERRED`
- VareduraAPIHandler `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*