---
title: "Varedura — safe Docker/WSL cleanup + network monitor"
cover_image: "/mascot/images/working_1.png"
tags: copilot, copilot-cli, python, docker, wsl, textual, cli, opensource
published: false
---

*This is a submission for the [GitHub Copilot CLI Challenge](https://dev.to/challenges/github-2026-01-21)*

# Varedura — safe Docker/WSL cleanup + network monitor 🧹⚡

## What I Built
Varedura is a focused toolkit that makes cleaning up Docker/WSL and monitoring local network activity painless. It combines a Textual TUI and a set of CLIs to:

- safely prune Docker resources (containers, images, volumes, builders),
- compact Windows VHDX files for WSL distributions,
- provide network speed and port‑scan monitoring,
- record short session GIFs and write daily logs.

All destructive actions require explicit confirmation and the test suite mocks external calls so CI never runs destructive commands. The app exposes both synchronous CLI methods (for scripts) and async streaming APIs (for TUI/workers).

## Demo
Repository: https://github.com/joaosnet/Varedura

Quick start (Windows recommended for VHDX tasks):

- Activate venv
  - `& .\.venv\Scripts\Activate.ps1`
- Run the Textual TUI (auto‑elevates on Windows when needed)
  - `uv run main.py`
- Run CLI cleaner (full)
  - `uv run python -m cli.main_cleaner`
- Quick prune
  - `uv run python -m cli.quick_cleanup`
- Run tests
  - `uv run pytest tests/ -v`

Tip: Use the `screenshots/` or `recordings/` folders for visuals when publishing. The app parses Docker output for lines like `Total reclaimed space:` to summarize results after a prune.

## My Experience with GitHub Copilot CLI
This project was created using **GitHub Copilot** (Editor + Copilot CLI) — Copilot helped me scaffold features, write tests, and iterate UI components quickly. I used it to:

- generate initial implementations and pair sync/async variants (e.g., `WSLDockerCleaner` + `*_async`),
- scaffold unit tests and safe mocks for subprocess and admin flows,
- prototype Textual screens and worker patterns,
- write reproducible CLI entry points and helpful README examples.

Practical impact: Copilot cut iteration time dramatically — I could try multiple implementations fast and focus on reviewing, testing, and hardening logic. Final code and decisions were reviewed and refined manually; Copilot provided the scaffolding and strong suggestions that sped up development.

---

If you want, I can open a draft PR adding this file or make adjustments to the content/front‑matter.

Author: @joaosnet
