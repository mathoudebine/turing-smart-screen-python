# ![Icon](https://raw.githubusercontent.com/mathoudebine/turing-smart-screen-python/main/res/icons/monitor-icon-17865/24.png) turing-smart-screen-python

### ⚠️ DISCLAIMER - PLEASE READ ⚠️

This project is **not affiliated, associated, authorized, endorsed by, or in any way officially connected with Turing or XuanFang brands**, or any of its subsidiaries, affiliates, manufacturers or sellers of the Turing or XuanFang products. All product and company names are the registered trademarks of their original owners.

This project is an open-source alternative software, NOT the USBMonitor.exe / ExtendScreen.exe or any original software for the smart screens (even if some themes have been reused). **Please do not open issues for USBMonitor.exe/ExtendScreen.exe here**, instead you can use:
* for Turing Smart Screen, the official forum here: http://discuz.turzx.com/
* for XuanFang Smart screen, contact your reseller
---

![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black) ![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white) ![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=apple&logoColor=white) ![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846?style=for-the-badge&logo=Raspberry%20Pi&logoColor=white) ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) [![Licence](https://img.shields.io/github/license/mathoudebine/turing-smart-screen-python?style=for-the-badge)](./LICENSE)
  

A Python system monitor program and a library for 3.5" IPS USB-C (UART) displays.  

Supported operating systems : macOS, Windows, Linux (incl. Raspberry Pi), basically all OS that support Python 3.x  

Supported smart screens models:
| **Turing Smart Screen** | **XuanFang** |
|--------|----------|
| <img src="https://ae01.alicdn.com/kf/S4cd5d420d8034c7e8ff1cb40fdad0bccR.jpg" height="300" /> |  <img src="https://ae01.alicdn.com/kf/S28f803263a05455e86c58fb8f2572815K.jpg" height="300" />        |
| also improperly called "revision A" by the resellers | revision B & flagship (with backplate & RGB LEDs) |

### [> What is my smart screen model?](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions)  

**Please note the Turing and the XuanFang screens are 2 different products** designed and produced by different companies, despite having a similar appearance. The communication protocol is also different.  
This project support both products, including backplate RGB LEDs for available models!

If you haven't received your screen yet but want to start developing your theme now, you can use the [**"simulated LCD" mode!**](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Simulated-display)



## How to use

### [> Follow instructions on the wiki to configure and start this project.](https://github.com/mathoudebine/turing-smart-screen-python/wiki)

There are 2 possible uses of this project Python code:
* **[as a System Monitor](#system-monitor)**, a standalone program working with themes to display your computer HW info.
[Check if your hardware is supported.](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-hardware-support)
* **[integrated in your project](#control-the-display-from-your-python-projects)**, to control the display from your own Python code.

## System monitor

This project is mainly a complete standalone program to use your screen as a system monitor, like the original vendor app.  
Some themes are already included for a quick start!
### [> Configure and start system monitor](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-how-to-start)
* Fully functional multi-OS code base (operates out of the box, tested on Windows, Linux & MacOS).
* Display configuration using `config.yaml` file: no Python code to edit.
* Support for all [3.5" smart screen models (Turing and XuanFang)](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions). Backplate RGB LEDs are also supported for available models!
* Support [multiple hardware sensors and metrics (CPU/GPU usage, temperatures, memory, disks, etc)](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-themes#stats-entry) with configurable refresh intervals.
* Allow [creation of themes (see `res/themes`) with `theme.yaml` files](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-themes) to be [shared with the community!](https://github.com/mathoudebine/turing-smart-screen-python/discussions/categories/themes)
* Easy to expand: additional code that pulls specific information can be written in a modular way without impacting existing code.
* Auto detect comm port. No longer need to hard set it, or if it changes on you then the config is wrong.
* Tray icon with Exit option, useful when the program is running in background

Screenshots from the latest version using included themes:  
<img src="res/docs/Theme3.5Inch.jpg" height="400" /> <img src="res/docs/ThemeTerminal.jpg" height="400" /> <img src="res/docs/ThemeCyberpunk.png" height="400" /> <img src="res/docs/ThemeBashDarkGreen.png" height="400" /> <img src="res/docs/ThemeLandscape6Grid.jpg" width="400" /> <img src="res/docs/ThemeLandscapeMagicBlue.png" width="400" />

### [> Themes creation/edition](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-themes)
### [> Themes shared by the community](https://github.com/mathoudebine/turing-smart-screen-python/discussions/categories/themes)

## Control the display from your Python projects

If you don't want to use your screen for system monitoring, you can just use this project as a module to do some simple operations on the display from any Python code :
- **Display custom picture**
- **Display text**
- **Display progress bar**
- **Screen rotation**
- Clear the screen (blank)
- Turn the screen on/off
- Display soft reset
- Set brightness
- Set backplate RGB LEDs color (on supported hardware rev.) 

Check `simple-program.py` as an example.

### [> Control the display from your code](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Control-screen-from-your-own-code)

## Troubleshooting
If you have trouble running the program as described in the wiki, please check [open/closed issues](https://github.com/mathoudebine/turing-smart-screen-python/issues) & [the wiki Troubleshooting page](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting)


