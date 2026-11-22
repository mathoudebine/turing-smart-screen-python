// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
//
// Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
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

// C++ port of theme-editor.py: edit themes for System Monitor in a preview window on the computer.
// The preview window is refreshed as soon as the theme file is modified.
// Phase 0 skeleton: an empty window.

#include "theme-editor.h"

ThemeEditorWindow::ThemeEditorWindow()
{
    set_title("Turing SysMon Theme Editor");
    set_default_size(640, 480);

    placeholder_label.set_text("Theme editor (C++ port): not implemented yet");
    set_child(placeholder_label);
}

int main(int argc, char *argv[])
{
    auto app = Gtk::Application::create("io.github.turing_smart_screen.ThemeEditor");
    return app->make_window_and_run<ThemeEditorWindow>(argc, argv);
}
