# AGENTS.md

## C++ Port (in progress)
- The Python code is being converted to C++. Target platform: **Linux only (Ubuntu 26.04 LTS)**; Windows and macOS support is dropped in the C++ code.
- C++ sources live in `src/` (`src/library/` mirrors `library/`, `src/tools/` mirrors `tools/`); C++ unit tests live in `tests/cpp/` (GoogleTest).
- Wherever possible, one Python file becomes one `.h` + `.cpp` pair with the same base name (program entry points such as `main.cpp` have no header).
- Build with the root `Makefile` (C++20, g++, dependencies found with `pkg-config`): `make deps`, `make`, `make test`, `make clean`. Programs are built into `build/bin/` (`main`, `configure`, `theme-editor`, `simple-program`).
- GUI programs (`configure`, `theme-editor`) use GTK 4 through gtkmm-4.0.
- Files without Python counterpart replace Python dependencies: `src/library/lcd/image` (Pillow `Image`/`ImageDraw`), `src/library/lcd/font` (Pillow `ImageFont` with raqm: FreeType + HarfBuzz), `src/library/lcd/serial_port` (pyserial, termios), `src/library/ping` (ping3, ICMP socket).
- `src/library/sensors/sensors_python` keeps its name (selected by `HW_SENSORS: PYTHON`/`AUTO`) but reads Linux `/proc` and `/sys` directly instead of psutil/GPUtil/pyamdgpuinfo, plus NVIDIA NVML loaded at runtime. Custom sensors (`sensors_custom`) are C++ classes registered in `custom_data_sources()`: adding one requires rebuilding.
- The library is initialized explicitly with `config::init()` (Python loads it on import); theme values are read with `config::get()` / `config::get_color()`, which return the default value for missing or empty keys.
- The rendering does not need to be pixel-identical to the Python/Pillow version, only close to it.
- `config.yaml` and `res/` (themes, fonts, images) are shared, unchanged, by the Python and C++ versions.
- The Python code stays complete and working until the C++ programs work end-to-end; then every converted Python file is deleted in one cleanup step. Until then, the Python sections below still describe the reference implementation, and the cross-platform rule applies to Python code only.
- Not converted: `library/pythoncheck.py`, `library/sensors/sensors_librehardwaremonitor.py` (Windows only), `tools/windows-installer/`.

## Project Goal
- Python system monitor for USB-C/TFT displays (Turing, XuanFang, Kipye, WeAct) with 3 usage modes: main app (`main.py`), config tool (`configure.py`), and theme editor (`theme-editor.py`).
- The design clearly separates **sensor collection**, **theme rendering**, and **hardware driver** so multiple display revisions can be supported without changing business logic.

## Essential Architecture (read before coding)
- **Application entry point**: `main.py` orchestrates initialization, scheduler loop, tray icon, and OS signals.
- **Central config**: `library/config.py` loads `config.yaml`, then `res/themes/<THEME>/theme.yaml` with fallback to defaults.
- **LCD driver factory**: `library/display.py` selects the implementation via `REVISION` (`A/B/C/D/TUR_USB/WEACT_A/WEACT_B/SIMU`).
- **Hardware drivers**: `library/lcd/` contains `LcdComm*` classes (serial/USB) with a uniform API (`InitializeComm`, `DisplayBitmap`, `DisplayText`, `SetBrightness`, etc.).
- **Sensors and stats rendering**: `library/stats.py` collects metrics (CPU/GPU/RAM/disk/net/weather) and applies theme styles.
- **Scheduling**: `library/scheduler.py` uses decorators (`@schedule`, `@async_job`) plus a queue to serialize writes to the display.

## Data Flow (practical)
- `config.yaml` -> selects hardware/theme/options.
- `library/stats.py` -> retrieves values based on `HW_SENSORS` (`AUTO`, `PYTHON`, `LHM`, `STUB`).
- `library/display.py` + `LcdComm*` driver -> converts to image/text and pushes to the display.
- Dev mode without hardware: `REVISION: SIMU` writes a capture (`screencap.png`) through `library/lcd/lcd_simulated.py`.

## Critical Developer Workflows
- Install dependencies: `pip install -r requirements.txt`.
- Run app: `python main.py`.
- Configure via GUI: `python configure.py`.
- LCD API usage example: `python simple-program.py`.
- Windows packaging: `pyinstaller turing-system-monitor.spec` (bundles `main`, `configure`, `theme-editor`, `res/`, `external/`, `config.yaml`).

## Repository-Specific Conventions
- License header expected in `.py` files: `SPDX-License-Identifier: GPL-3.0-or-later` (see `main.py`).
- YAML-first configuration: avoid hardcoding; add options in `config.yaml` first, then load them in `library/config.py`.
- The project is multi-platform (Windows, macOS, Linux): new code must remain compatible across these platforms.
- Platform-specific code blocks are allowed when required, but prefer direct cross-platform implementations whenever possible.
- Hardware routing goes through `REVISION`; do not add a new revision outside the factory in `library/display.py`.
- Periodic updates go through `library/scheduler.py` (avoid ad-hoc parallel loops that write to the device).
- UI rendering depends on theme keys (example structure in `res/themes/default.yaml`): keep schema compatibility.

## PR Change Policy
- Keep pull request changes as limited and focused as possible; avoid broad refactors unless explicitly requested.
- This repository has many users, forks, and open PRs: prefer minimal diffs to reduce merge conflicts and downstream breakage.
- If changes touch different topics, split them into multiple PRs (one topic per PR).
- If a PR is large, split it into several smaller PRs that can be reviewed and merged independently.
- Assume every PR is reviewed by a human maintainer; write clear, reviewable commits and preserve existing behavior by default.
- Breaking changes are unlikely to be merged; maintain backward compatibility unless a maintainer explicitly approves a compatibility break.

## Important External Integrations
- `pyserial` for serial displays (A/B/C/D, WeAct), `pyusb` for Turing USB models.
- Advanced Windows sensors: `pythonnet` + DLLs in `external/LibreHardwareMonitor/`.
- System metrics: `psutil`, `GPUtil`, `pyamdgpuinfo`/`pyadl` depending on OS/GPU.
- UI stack: `pystray` (tray), `tkinter` + `sv-ttk` (config GUI), `Pillow`/`numpy` (images).

## Reference Files for Changes
- Runtime orchestration: `main.py`
- Config/theme loading: `library/config.py`
- Display selection and dimensions: `library/display.py`
- Scheduler/periodic jobs: `library/scheduler.py`
- Sensor collection/rendering: `library/stats.py`
- User config schema: `config.yaml`
- Low-level API example: `simple-program.py`
- Executable build spec: `turing-system-monitor.spec`


