// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

// System tray icon with a menu, replacing the pystray Python library used by main.py.
// No Python counterpart: this file replaces a Python dependency.
//
// Uses the freedesktop StatusNotifierItem D-Bus protocol (with a com.canonical.dbusmenu menu), supported by KDE,
// Xfce, Cinnamon, MATE, Budgie... and by GNOME with the AppIndicator extension (installed by default on Ubuntu).

#pragma once

#include <functional>
#include <string>
#include <thread>
#include <vector>

class TrayIcon
{
public:
    struct MenuItem
    {
        std::string label;  // empty label: separator
        std::function<void()> action;
    };

    // icon_paths: PNG files of the icon (several sizes can be given)
    TrayIcon(std::string name, std::string title, std::vector<std::string> icon_paths, std::vector<MenuItem> menu);
    ~TrayIcon();

    TrayIcon(const TrayIcon &) = delete;
    TrayIcon &operator=(const TrayIcon &) = delete;

    // Display the tray icon from a background thread. Returns false if there is no D-Bus session bus.
    bool run_detached();

    // Remove the tray icon
    void stop();

    // Called from the D-Bus thread
    struct Private;

private:
    Private *d;
    std::thread thread;
};
