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

// C++ port of configure.py: the system monitor configuration GUI (GTK 4 with gtkmm).
// Values are written to config.yaml keeping its comments and formatting.

#pragma once

#include <map>
#include <string>
#include <vector>

#include <gtkmm.h>
#include <yaml-cpp/yaml.h>

// Drop-down list of strings (replaces ttk.Combobox in read-only mode)
class StringDropDown : public Gtk::DropDown
{
public:
    StringDropDown();
    explicit StringDropDown(const std::vector<std::string> &items);

    void set_items(const std::vector<std::string> &items);
    std::vector<std::string> get_items() const;

    // Select the item with this text. If the text is not in the list, it is added at the end (like ttk.Combobox,
    // which can display a value that is not in its list)
    void set_text(const std::string &text);
    std::string get_text() const;

    // Index of the selected item, -1 if none
    int current() const;
    void set_current(int index);

private:
    Glib::RefPtr<Gtk::StringList> list;
};

class TuringConfigWindow;

// Sub-window for weather & ping configuration
class MoreConfigWindow : public Gtk::Window
{
public:
    explicit MoreConfigWindow(TuringConfigWindow &main_window);

    void load_config_values(const YAML::Node &config);
    void show_window();

private:
    void citysearch_show_warning(const std::string &warning);
    void on_search_click();
    void on_filllatlong_click();
    void on_save_click();
    void save_config_values();
    // Coordinates entries only accept a decimal number
    void setup_coordinate_entry(Gtk::Entry &entry, std::string &last_valid);

    struct CityEntry
    {
        std::string full_name;
        std::string lat;
        std::string lon;
    };

    TuringConfigWindow &main_window;
    Gtk::Fixed layout;
    Gtk::Entry ping_entry, api_entry, lat_entry, long_entry, citysearch_entry;
    std::string lat_last_valid, long_last_valid;
    StringDropDown unit_cb, lang_cb, citysearch_cb;
    Gtk::Label citysearch_warn_label;
    std::vector<CityEntry> city_entries;
};

class TuringConfigWindow : public Gtk::ApplicationWindow
{
public:
    TuringConfigWindow();

    void save_additional_config(const std::string &ping, const std::string &api_key, const std::string &lat,
                                const std::string &lon, const std::string &unit, const std::string &lang);

private:
    void load_theme_preview();
    void load_config_values();
    // Returns false (with an error message) if the values cannot be saved
    bool save_config_values();

    void on_theme_change();
    void on_open_theme_folder_click();
    void on_theme_editor_click();
    void on_save_click();
    void on_saverun_click();
    void on_brightness_change();
    void on_model_change();
    void on_size_change();
    void on_hwlib_change();
    void show_hide_brightness_warning();
    bool on_fan_speed_update();
    void show_error(const std::string &message);

    Gtk::Fixed layout;
    Gtk::Picture theme_preview;
    Gtk::Label theme_author;
    StringDropDown model_cb, size_cb, com_cb, orient_cb, theme_cb, hwlib_cb, eth_cb, wl_cb, cpu_fan_cb;
    Gtk::Scale brightness_slider;
    Gtk::Label brightness_val_label, brightness_warning_label, cpu_fan_label;
    Gtk::Button weather_ping_btn, open_theme_folder_btn, edit_theme_btn, save_btn, save_run_btn;

    MoreConfigWindow more_config_window;
};
