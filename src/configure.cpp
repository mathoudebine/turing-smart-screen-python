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

#include "configure.h"

#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <format>
#include <fstream>
#include <set>

#include <curl/curl.h>
#include <ifaddrs.h>
#include <unicode/locid.h>
#include <unicode/unistr.h>

#include "library/config.h"
#include "library/lcd/serial_port.h"
#include "library/log.h"
#include "library/sensors/sensors_python.h"

namespace fs = std::filesystem;

namespace {

const std::string TURING_MODEL = "Turing Smart Screen";
const std::string USBPCMONITOR_MODEL = "UsbPCMonitor";
const std::string XUANFANG_MODEL = "XuanFang rev. B & flagship";
const std::string KIPYE_MODEL = "Kipye Qiye Smart Display";
const std::string WEACT_MODEL = "WeAct Studio Display FS V1";
const std::string SIMULATED_MODEL = "Simulated screen";

const std::string _SIZE_2_1_INCH = "2.1\"";  // Only for retro compatibility
const std::string _SIZE_2_8_INCH = "2.8\"";  // Only for retro compatibility
const std::string _SIZE_9_2_INCH = "9.2\"";  // Only for retro compatibility
const std::string SIZE_0_96_INCH = "0.96\"";
const std::string SIZE_2_x_INCH = "2.1\" / 2.8\"";
const std::string SIZE_3_5_INCH = "3.5\"";
const std::string SIZE_4_6_INCH = "4.6\"";
const std::string SIZE_5_INCH = "5\"";
const std::string SIZE_5_2_INCH = "5.2\"";
const std::string SIZE_8_INCH = "8\"";
const std::string SIZE_8_8_INCH = "8.8\"";
const std::string SIZE_8_8_INCH_NEWREV = "8.8\" / 9.2\" (V1.X new HW rev.)";
const std::string SIZE_12_3_INCH = "12.3\"";
const std::string SIZE_2_8_INCH_NEWREV = "2.8\" round (V1.X new HW rev.)";

// List of sizes that can be selected
const std::vector<std::string> size_list = {
    SIZE_0_96_INCH, SIZE_2_x_INCH, SIZE_2_8_INCH_NEWREV, SIZE_3_5_INCH, SIZE_4_6_INCH, SIZE_5_INCH,
    SIZE_5_2_INCH, SIZE_8_INCH, SIZE_8_8_INCH, SIZE_8_8_INCH_NEWREV, SIZE_12_3_INCH,
};

using RevisionSize = std::pair<std::string, std::string>;

// Maps between config.yaml values and GUI description
// This map is used to select the correct smart screen model based on config.yaml "REVISION" and selected "THEME" size
const std::vector<std::pair<RevisionSize, std::string>> revision_and_size_to_model_map = {
    {{"A", SIZE_3_5_INCH}, TURING_MODEL},  // Can also be UsbPCMonitor 3.5, does not matter since protocol is the same
    {{"A", SIZE_5_INCH}, USBPCMONITOR_MODEL},
    {{"B", SIZE_3_5_INCH}, XUANFANG_MODEL},
    {{"C", SIZE_2_x_INCH}, TURING_MODEL},
    {{"C", SIZE_5_INCH}, TURING_MODEL},
    {{"C", SIZE_8_8_INCH}, TURING_MODEL},
    {{"D", SIZE_3_5_INCH}, KIPYE_MODEL},
    {{"TUR_USB", SIZE_4_6_INCH}, TURING_MODEL},
    {{"TUR_USB", SIZE_5_2_INCH}, TURING_MODEL},
    {{"TUR_USB", SIZE_8_INCH}, TURING_MODEL},
    {{"TUR_USB", SIZE_8_8_INCH}, TURING_MODEL},
    {{"TUR_USB", SIZE_8_8_INCH_NEWREV}, TURING_MODEL},
    {{"TUR_USB", SIZE_12_3_INCH}, TURING_MODEL},
    {{"TUR_USB", SIZE_2_8_INCH_NEWREV}, TURING_MODEL},
    {{"WEACT_A", SIZE_3_5_INCH}, WEACT_MODEL},
    {{"WEACT_B", SIZE_0_96_INCH}, WEACT_MODEL},

    {{"SIMU", SIZE_0_96_INCH}, SIMULATED_MODEL},
    {{"SIMU", SIZE_2_x_INCH}, SIMULATED_MODEL},
    {{"SIMU", SIZE_3_5_INCH}, SIMULATED_MODEL},
    {{"SIMU", SIZE_4_6_INCH}, SIMULATED_MODEL},
    {{"SIMU", SIZE_5_INCH}, SIMULATED_MODEL},
    {{"SIMU", SIZE_5_2_INCH}, SIMULATED_MODEL},
    {{"SIMU", SIZE_8_INCH}, SIMULATED_MODEL},
    {{"SIMU", SIZE_8_8_INCH}, SIMULATED_MODEL},
};

// This map is used to write the correct config.yaml "REVISION" from selected smart screen model and size
const std::map<std::pair<std::string, std::string>, std::string> model_and_size_to_revision_map = {
    {{KIPYE_MODEL, SIZE_3_5_INCH}, "D"},
    {{TURING_MODEL, SIZE_2_x_INCH}, "C"},
    {{TURING_MODEL, SIZE_3_5_INCH}, "A"},
    {{TURING_MODEL, SIZE_4_6_INCH}, "TUR_USB"},
    {{TURING_MODEL, SIZE_5_2_INCH}, "TUR_USB"},
    {{TURING_MODEL, SIZE_5_INCH}, "C"},
    {{TURING_MODEL, SIZE_8_INCH}, "TUR_USB"},
    {{TURING_MODEL, SIZE_8_8_INCH}, "C"},
    {{TURING_MODEL, SIZE_8_8_INCH_NEWREV}, "TUR_USB"},
    {{TURING_MODEL, SIZE_12_3_INCH}, "TUR_USB"},
    {{TURING_MODEL, SIZE_2_8_INCH_NEWREV}, "TUR_USB"},
    {{USBPCMONITOR_MODEL, SIZE_3_5_INCH}, "A"},
    {{USBPCMONITOR_MODEL, SIZE_5_INCH}, "A"},
    {{WEACT_MODEL, SIZE_0_96_INCH}, "WEACT_B"},
    {{WEACT_MODEL, SIZE_3_5_INCH}, "WEACT_A"},
    {{XUANFANG_MODEL, SIZE_3_5_INCH}, "B"},

    {{SIMULATED_MODEL, SIZE_0_96_INCH}, "SIMU"},
    {{SIMULATED_MODEL, SIZE_2_x_INCH}, "SIMU"},
    {{SIMULATED_MODEL, SIZE_3_5_INCH}, "SIMU"},
    {{SIMULATED_MODEL, SIZE_4_6_INCH}, "SIMU"},
    {{SIMULATED_MODEL, SIZE_5_INCH}, "SIMU"},
    {{SIMULATED_MODEL, SIZE_5_2_INCH}, "SIMU"},
    {{SIMULATED_MODEL, SIZE_8_INCH}, "SIMU"},
    {{SIMULATED_MODEL, SIZE_8_8_INCH}, "SIMU"},
};

// LibreHardwareMonitor (LHM) is for Windows platforms only
const std::vector<std::pair<std::string, std::string>> hw_lib_map = {
    {"AUTO", "Automatic"}, {"PYTHON", "Python libraries"}, {"STUB", "Fake random data"}, {"STATIC", "Fake static data"}};
const std::vector<std::pair<bool, std::string>> reverse_map = {{false, "classic"}, {true, "reverse"}};
const std::vector<std::pair<std::string, std::string>> weather_unit_map = {
    {"metric", "metric - °C"}, {"imperial", "imperial - °F"}, {"standard", "standard - °K"}};
const std::vector<std::pair<std::string, std::string>> weather_lang_map = {
    {"sq", "Albanian"}, {"af", "Afrikaans"}, {"ar", "Arabic"}, {"az", "Azerbaijani"}, {"eu", "Basque"},
    {"be", "Belarusian"}, {"bg", "Bulgarian"}, {"ca", "Catalan"}, {"zh_cn", "Chinese Simplified"},
    {"zh_tw", "Chinese Traditional"}, {"hr", "Croatian"}, {"cz", "Czech"}, {"da", "Danish"}, {"nl", "Dutch"},
    {"en", "English"}, {"fi", "Finnish"}, {"fr", "French"}, {"gl", "Galician"}, {"de", "German"}, {"el", "Greek"},
    {"he", "Hebrew"}, {"hi", "Hindi"}, {"hu", "Hungarian"}, {"is", "Icelandic"}, {"id", "Indonesian"},
    {"it", "Italian"}, {"ja", "Japanese"}, {"kr", "Korean"}, {"ku", "Kurmanji (Kurdish)"}, {"la", "Latvian"},
    {"lt", "Lithuanian"}, {"mk", "Macedonian"}, {"no", "Norwegian"}, {"fa", "Persian (Farsi)"}, {"pl", "Polish"},
    {"pt", "Portuguese"}, {"pt_br", "Português Brasil"}, {"ro", "Romanian"}, {"ru", "Russian"}, {"sr", "Serbian"},
    {"sk", "Slovak"}, {"sl", "Slovenian"}, {"sp", "Spanish"}, {"sv", "Swedish"}, {"th", "Thai"}, {"tr", "Turkish"},
    {"ua", "Ukrainian"}, {"vi", "Vietnamese"}, {"zu", "Zulu"}};

const std::string ORANGE_TEXT_COLOR = "#FF8C00";
const std::string RED_TEXT_COLOR = "#E01B24";

template<typename K>
std::vector<std::string> map_values(const std::vector<std::pair<K, std::string>> &map)
{
    std::vector<std::string> values;
    for (const auto &[key, value]: map) {
        values.push_back(value);
    }
    return values;
}

template<typename K>
std::optional<std::string> map_value(const std::vector<std::pair<K, std::string>> &map, const K &key)
{
    for (const auto &[k, v]: map) {
        if (k == key) return v;
    }
    return std::nullopt;
}

template<typename K>
std::optional<K> map_key(const std::vector<std::pair<K, std::string>> &map, const std::string &value)
{
    for (const auto &[k, v]: map) {
        if (v == value) return k;
    }
    return std::nullopt;
}

fs::path main_directory()
{
    static const fs::path dir = config::find_main_directory();
    return dir;
}

fs::path themes_dir()
{
    return main_directory() / "res" / "themes";
}

// Directory containing this program (build/bin/), where the other programs are
fs::path program_directory()
{
    std::error_code ec;
    const fs::path exe = fs::read_symlink("/proc/self/exe", ec);
    return ec ? fs::current_path() : exe.parent_path();
}

std::optional<YAML::Node> get_theme_data(const std::string &name)
{
    const fs::path theme = themes_dir() / name / "theme.yaml";
    std::error_code ec;
    if (name.empty() || !fs::is_regular_file(theme, ec)) {
        return std::nullopt;
    }
    try {
        return YAML::LoadFile(theme.string());
    } catch (const YAML::Exception &) {
        return std::nullopt;
    }
}

std::string theme_display_size(const YAML::Node &theme_data)
{
    return config::get(theme_data["display"], "DISPLAY_SIZE", "3.5\"");
}

std::vector<std::string> get_themes(const std::string &size)
{
    std::vector<std::string> themes;
    std::error_code ec;
    for (const auto &entry: fs::directory_iterator(themes_dir(), ec)) {
        const std::string name = entry.path().filename().string();
        const auto theme_data = get_theme_data(name);
        if (theme_data && theme_display_size(*theme_data) == size) {
            themes.push_back(name);
        }
    }
    // Case-insensitive sort
    std::sort(themes.begin(), themes.end(), [](const std::string &a, const std::string &b) {
        return std::lexicographical_compare(a.begin(), a.end(), b.begin(), b.end(), [](unsigned char x, unsigned char y) {
            return std::tolower(x) < std::tolower(y);
        });
    });
    return themes;
}

std::string get_theme_size(const std::string &name)
{
    const auto theme_data = get_theme_data(name);
    return theme_data ? theme_display_size(*theme_data) : "3.5\"";
}

std::vector<std::string> get_com_ports()
{
    std::vector<std::string> com_ports_names = {"Automatic detection"};  // Add manual entry on top for auto-detection
    for (const auto &com_port: comports()) {
        com_ports_names.push_back(com_port.device);
    }
    return com_ports_names;
}

std::vector<std::string> get_net_if()
{
    std::vector<std::string> if_list = {"None"};  // Add manual entry on top for unavailable/not selected interface
    ifaddrs *addresses = nullptr;
    if (getifaddrs(&addresses) == 0) {
        for (ifaddrs *a = addresses; a; a = a->ifa_next) {
            if (a->ifa_name && std::find(if_list.begin(), if_list.end(), a->ifa_name) == if_list.end()) {
                if_list.emplace_back(a->ifa_name);
            }
        }
        freeifaddrs(addresses);
    }
    return if_list;
}

std::vector<std::string> get_fans()
{
    std::vector<std::string> fan_list;
    std::string auto_detected_cpu_fan = "None";
    for (const auto &[name, entries]: sensors_python::sensors_fans()) {
        for (const auto &entry: entries) {
            fan_list.push_back(std::format("{}/{} ({}% - {} RPM)", name, entry.label, entry.percent, entry.current));
            if ((sensors_python::is_cpu_fan(entry.label) || sensors_python::is_cpu_fan(name)) &&
                auto_detected_cpu_fan == "None") {
                auto_detected_cpu_fan = std::format("Auto-detected: {}/{}", name, entry.label);
            }
        }
    }
    fan_list.insert(fan_list.begin(), auto_detected_cpu_fan);  // Add manual entry on top if auto-detection succeeded
    return fan_list;
}

std::string get_version()
{
    std::ifstream version_file(main_directory() / "version.txt");
    std::string version;
    if (version_file && std::getline(version_file, version) && !version.empty()) {
        return version;
    }
    const std::string command = "git -C '" + main_directory().string() + "' rev-parse --short HEAD 2>/dev/null";
    if (FILE *pipe = popen(command.c_str(), "r")) {
        char buffer[64] = {};
        if (fgets(buffer, sizeof(buffer), pipe)) {
            version = buffer;
            version.erase(version.find_last_not_of(" \n\r") + 1);
        }
        pclose(pipe);
    }
    return version.empty() ? "0.0.0" : version;
}

// Start a program of this project (built in the same directory) without waiting for it
void start_program(const std::string &program, const std::vector<std::string> &args = {})
{
    std::vector<std::string> argv = {(program_directory() / program).string()};
    argv.insert(argv.end(), args.begin(), args.end());
    try {
        Glib::spawn_async(main_directory().string(), argv);
    } catch (const Glib::Error &e) {
        logger.error("Cannot start {}: {}", argv[0], e.what());
    }
}

void place(Gtk::Fixed &layout, Gtk::Widget &widget, int x, int y, int width = -1, int height = -1)
{
    widget.set_size_request(width, height);
    layout.put(widget, x, y);
}

Gtk::Label *bold_label(const std::string &text)
{
    auto *label = Gtk::make_managed<Gtk::Label>();
    label->set_markup("<b>" + Glib::Markup::escape_text(text) + "</b>");
    return label;
}

Gtk::Label *link_label(const std::string &text, const std::string &url)
{
    auto *label = Gtk::make_managed<Gtk::Label>();
    label->set_markup("<a href=\"" + Glib::Markup::escape_text(url) + "\">" + Glib::Markup::escape_text(text) + "</a>");
    return label;
}

size_t curl_write(char *ptr, size_t size, size_t nmemb, void *userdata)
{
    static_cast<std::string *>(userdata)->append(ptr, size * nmemb);
    return size * nmemb;
}

}  // namespace

// ---------------------------------------------------------------------------------------------------------------------
// StringDropDown

StringDropDown::StringDropDown() : StringDropDown(std::vector<std::string>{})
{
}

StringDropDown::StringDropDown(const std::vector<std::string> &items) : list(Gtk::StringList::create({}))
{
    set_model(list);
    set_items(items);
}

void StringDropDown::set_items(const std::vector<std::string> &items)
{
    std::vector<Glib::ustring> values(items.begin(), items.end());
    list->splice(0, list->get_n_items(), values);
}

std::vector<std::string> StringDropDown::get_items() const
{
    std::vector<std::string> items;
    for (guint i = 0; i < list->get_n_items(); i++) {
        items.push_back(list->get_string(i));
    }
    return items;
}

void StringDropDown::set_text(const std::string &text)
{
    const auto items = get_items();
    const auto it = std::find(items.begin(), items.end(), text);
    if (it != items.end()) {
        set_selected(static_cast<guint>(it - items.begin()));
    } else {
        list->append(text);
        set_selected(list->get_n_items() - 1);
    }
}

std::string StringDropDown::get_text() const
{
    const guint selected = get_selected();
    return selected == GTK_INVALID_LIST_POSITION || selected >= list->get_n_items() ? "" : list->get_string(selected);
}

int StringDropDown::current() const
{
    const guint selected = get_selected();
    return selected == GTK_INVALID_LIST_POSITION ? -1 : static_cast<int>(selected);
}

void StringDropDown::set_current(int index)
{
    if (index >= 0 && static_cast<guint>(index) < list->get_n_items()) {
        set_selected(static_cast<guint>(index));
    }
}

// ---------------------------------------------------------------------------------------------------------------------
// TuringConfigWindow

TuringConfigWindow::TuringConfigWindow()
    : model_cb(std::vector<std::string>{TURING_MODEL, USBPCMONITOR_MODEL, XUANFANG_MODEL, KIPYE_MODEL, WEACT_MODEL,
                                        SIMULATED_MODEL}),
      size_cb(size_list), com_cb(get_com_ports()), orient_cb(map_values(reverse_map)), hwlib_cb(map_values(hw_lib_map)),
      eth_cb(get_net_if()), wl_cb(get_net_if()), cpu_fan_cb(get_fans()),
      brightness_slider(Gtk::Adjustment::create(50, 0, 100, 1, 10), Gtk::Orientation::HORIZONTAL),
      more_config_window(*this)
{
    set_title("Turing System Monitor configuration");
    set_default_size(820, 590);
    set_child(layout);

    // When window gets focus again, reload theme preview in case it has been updated by theme editor
    property_is_active().signal_changed().connect([this] {
        if (is_active()) {
            on_theme_change();
        }
    });

    Glib::signal_timeout().connect(sigc::mem_fun(*this, &TuringConfigWindow::on_fan_speed_update), 500);

    theme_preview.set_can_shrink(false);
    place(layout, theme_preview, 10, 10);
    layout.put(theme_author, 10, 500);

    place(layout, *bold_label("Display configuration"), 370, 0);

    place(layout, *Gtk::make_managed<Gtk::Label>("Smart screen model"), 370, 35);
    model_cb.property_selected().signal_changed().connect(sigc::mem_fun(*this, &TuringConfigWindow::on_model_change));
    place(layout, model_cb, 550, 30, 250);

    place(layout, *Gtk::make_managed<Gtk::Label>("Smart screen size"), 370, 75);
    size_cb.property_selected().signal_changed().connect(sigc::mem_fun(*this, &TuringConfigWindow::on_size_change));
    place(layout, size_cb, 550, 70, 250);

    place(layout, *Gtk::make_managed<Gtk::Label>("COM port"), 370, 115);
    place(layout, com_cb, 550, 110, 250);

    place(layout, *Gtk::make_managed<Gtk::Label>("Orientation"), 370, 155);
    place(layout, orient_cb, 550, 150, 250);

    place(layout, *Gtk::make_managed<Gtk::Label>("Brightness"), 370, 195);
    brightness_slider.set_draw_value(false);
    brightness_slider.signal_value_changed().connect(sigc::mem_fun(*this, &TuringConfigWindow::on_brightness_change));
    place(layout, brightness_slider, 600, 190, 180);
    place(layout, brightness_val_label, 550, 195);
    brightness_warning_label.set_markup("<span foreground=\"" + ORANGE_TEXT_COLOR +
                                        "\">⚠ Turing 3.5\" displays can get hot at high brightness!</span>");
    place(layout, brightness_warning_label, 370, 225);

    place(layout, *bold_label("System Monitor Configuration"), 370, 260);

    place(layout, *Gtk::make_managed<Gtk::Label>("Theme"), 370, 300);
    theme_cb.property_selected().signal_changed().connect(sigc::mem_fun(*this, &TuringConfigWindow::on_theme_change));
    place(layout, theme_cb, 550, 295, 250);

    place(layout, *Gtk::make_managed<Gtk::Label>("Hardware monitoring"), 370, 340);
    hwlib_cb.property_selected().signal_changed().connect(sigc::mem_fun(*this, &TuringConfigWindow::on_hwlib_change));
    place(layout, hwlib_cb, 550, 335, 250);

    place(layout, *Gtk::make_managed<Gtk::Label>("Ethernet interface"), 370, 380);
    place(layout, eth_cb, 550, 375, 250);

    place(layout, *Gtk::make_managed<Gtk::Label>("Wi-Fi interface"), 370, 420);
    place(layout, wl_cb, 550, 415, 250);

    cpu_fan_label.set_markup("<u>CPU fan (？)</u>");
    cpu_fan_label.set_tooltip_text("If \"None\" is selected, CPU fan was not auto-detected.\n"
                                   "Manually select your CPU fan from the list.\n\n"
                                   "Fans missing from the list? Install lm-sensors package\n"
                                   "and run 'sudo sensors-detect' command, then reboot.");
    place(layout, cpu_fan_label, 370, 460);
    place(layout, cpu_fan_cb, 550, 455, 250);

    auto *version_label = Gtk::make_managed<Gtk::Label>();
    version_label->set_markup("<span alpha=\"60%\">" + Glib::Markup::escape_text(get_version()) + "</span>");
    place(layout, *version_label, 5, 560);

    weather_ping_btn.set_label("⛅  Weather\n& Ping");
    weather_ping_btn.signal_clicked().connect([this] { more_config_window.show_window(); });
    place(layout, weather_ping_btn, 80, 520, 130, 60);

    open_theme_folder_btn.set_label("📂  Open themes\nfolder");
    open_theme_folder_btn.signal_clicked().connect(
        sigc::mem_fun(*this, &TuringConfigWindow::on_open_theme_folder_click));
    place(layout, open_theme_folder_btn, 220, 520, 130, 60);

    edit_theme_btn.set_label("🎨  Edit theme");
    edit_theme_btn.signal_clicked().connect(sigc::mem_fun(*this, &TuringConfigWindow::on_theme_editor_click));
    place(layout, edit_theme_btn, 360, 520, 130, 60);

    save_btn.set_label("💾  Save settings");
    save_btn.signal_clicked().connect(sigc::mem_fun(*this, &TuringConfigWindow::on_save_click));
    place(layout, save_btn, 500, 520, 130, 60);

    save_run_btn.set_label("▶️  Save and run");
    save_run_btn.signal_clicked().connect(sigc::mem_fun(*this, &TuringConfigWindow::on_saverun_click));
    place(layout, save_run_btn, 640, 520, 140, 60);

    for (Gtk::Button *button: {&weather_ping_btn, &open_theme_folder_btn, &edit_theme_btn, &save_btn, &save_run_btn}) {
        if (auto *label = dynamic_cast<Gtk::Label *>(button->get_child())) {
            label->set_wrap(true);
            label->set_justify(Gtk::Justification::CENTER);
        }
    }

    more_config_window.set_transient_for(*this);

    load_config_values();
}

void TuringConfigWindow::load_theme_preview()
{
    const std::string theme = theme_cb.get_text();
    const auto theme_data = get_theme_data(theme);

    Glib::RefPtr<Gdk::Pixbuf> preview;
    try {
        preview = Gdk::Pixbuf::create_from_file((themes_dir() / theme / "preview.png").string());
        if (theme_data && theme_display_size(*theme_data) == _SIZE_2_1_INCH) {
            // This is a circular screen: apply a circle mask over the preview
            const auto mask = Gdk::Pixbuf::create_from_file(
                (main_directory() / "res/backgrounds/circular-mask.png").string());
            const int w = std::min(mask->get_width(), preview->get_width());
            const int h = std::min(mask->get_height(), preview->get_height());
            mask->composite(preview, 0, 0, w, h, 0, 0, 1, 1, Gdk::InterpType::NEAREST, 255);
        }
    } catch (const Glib::Error &) {
        try {
            preview = Gdk::Pixbuf::create_from_file((main_directory() / "res/docs/no-preview.png").string());
        } catch (const Glib::Error &) {
            preview.reset();
        }
    }

    int preview_height = 20;
    if (preview) {
        // Thumbnail: fit into 320x480, keeping the aspect ratio (never enlarged)
        const double scale = std::min({1.0, 320.0 / preview->get_width(), 480.0 / preview->get_height()});
        const int width = std::max(1, static_cast<int>(preview->get_width() * scale));
        const int height = std::max(1, static_cast<int>(preview->get_height() * scale));
        if (scale < 1.0) {
            preview = preview->scale_simple(width, height, Gdk::InterpType::HYPER);
        }
        theme_preview.set_paintable(Gdk::Texture::create_for_pixbuf(preview));
        theme_preview.set_size_request(width, height);
        preview_height = height;
    } else {
        theme_preview.set_paintable(nullptr);
        theme_preview.set_size_request(320, 20);
    }

    const std::string author_name = theme_data ? config::get(*theme_data, "author", "unknown") : "unknown";
    if (author_name.starts_with("@")) {
        theme_author.set_markup("Author: <a href=\"https://github.com/" +
                                Glib::Markup::escape_text(author_name.substr(1)) + "\">" +
                                Glib::Markup::escape_text(author_name) + "</a>");
    } else {
        theme_author.set_markup("<span alpha=\"60%\">Author: " + Glib::Markup::escape_text(author_name) + "</span>");
    }
    layout.move(theme_author, 10, preview_height + 15);
}

void TuringConfigWindow::load_config_values()
{
    YAML::Node cfg;
    try {
        cfg = YAML::LoadFile((main_directory() / "config.yaml").string());
    } catch (const YAML::Exception &e) {
        logger.error("Cannot load config.yaml: {}", e.what());
        cfg = YAML::Node(YAML::NodeType::Map);
    }
    const YAML::Node &c = cfg;
    const YAML::Node conf = c["config"];
    const YAML::Node display = c["display"];

    // Check if theme is valid
    std::string theme = config::get(conf, "THEME", "");
    if (!get_theme_data(theme)) {
        // Theme from config.yaml is not valid: use first theme available default size 3.5"
        const auto themes = get_themes(SIZE_3_5_INCH);
        theme = themes.empty() ? "" : themes.front();
    }
    theme_cb.set_text(theme);

    load_theme_preview();

    if (const auto hwlib = map_value(hw_lib_map, config::get(conf, "HW_SENSORS", "AUTO"))) {
        hwlib_cb.set_text(*hwlib);
    } else {
        hwlib_cb.set_current(0);
    }

    const std::string eth = config::get(conf, "ETH", "");
    eth.empty() ? eth_cb.set_current(0) : eth_cb.set_text(eth);

    const std::string wlo = config::get(conf, "WLO", "");
    wlo.empty() ? wl_cb.set_current(0) : wl_cb.set_text(wlo);

    std::string com_port = config::get(conf, "COM_PORT", "AUTO");
    if (com_port == "AUTO") {
        com_cb.set_current(0);
    } else {
        // Port name without directory (written by the Python version): devices are listed with their full path
        if (com_port.find('/') == std::string::npos) {
            com_port = "/dev/" + com_port;
        }
        com_cb.set_text(com_port);
    }

    // Guess display size from theme in the configuration
    const std::string revision = config::get(display, "REVISION", "A");
    std::string size = get_theme_size(theme);
    if (size == _SIZE_2_1_INCH || size == _SIZE_2_8_INCH) {
        size = SIZE_2_x_INCH;  // If a theme is for 2.1" or 2.8" then it is for all 2.x"
    } else if (size == _SIZE_9_2_INCH) {
        size = SIZE_8_8_INCH_NEWREV;  // If a theme is for 9.2" then it is for 8.8"/9.2" (new rev)
    }
    if (size == SIZE_8_8_INCH && revision == "TUR_USB") {
        size = SIZE_8_8_INCH_NEWREV;
    }
    if (size == SIZE_2_x_INCH && revision == "TUR_USB") {
        size = SIZE_2_8_INCH_NEWREV;
    }
    if (std::find(size_list.begin(), size_list.end(), size) != size_list.end()) {
        size_cb.set_text(size);
    } else {
        size_cb.set_current(0);
    }

    // Guess model from revision and size
    if (const auto model = map_value(revision_and_size_to_model_map, RevisionSize{revision, size})) {
        model_cb.set_text(*model);
    } else {
        model_cb.set_current(0);
    }

    orient_cb.set_text(*map_value(reverse_map, config::get(display, "DISPLAY_REVERSE", false)));

    brightness_slider.set_value(config::get(display, "BRIGHTNESS", 50));

    const std::string cpu_fan = config::get(conf, "CPU_FAN", "AUTO");
    if (cpu_fan == "AUTO") {
        cpu_fan_cb.set_current(0);
    } else {
        cpu_fan_cb.set_text(cpu_fan);
    }

    // Reload content on screen
    on_model_change();
    on_size_change();
    on_theme_change();
    on_brightness_change();
    on_hwlib_change();

    // Load configuration to sub-window as well
    more_config_window.load_config_values(cfg);
}

bool TuringConfigWindow::save_config_values()
{
    const auto revision = model_and_size_to_revision_map.find({model_cb.get_text(), size_cb.get_text()});
    if (revision == model_and_size_to_revision_map.end()) {
        show_error("The selected smart screen model is not available in size " + size_cb.get_text());
        return false;
    }

    std::string cpu_fan = "AUTO";
    if (cpu_fan_cb.current() > 0) {
        cpu_fan = cpu_fan_cb.get_text();
        cpu_fan = cpu_fan.substr(0, cpu_fan.find(' '));
    }

    try {
        config::update_yaml_file(main_directory() / "config.yaml", {
            {"config", "THEME", config::yaml_scalar(theme_cb.get_text())},
            {"config", "HW_SENSORS", map_key(hw_lib_map, hwlib_cb.get_text()).value_or("AUTO")},
            {"config", "ETH", config::yaml_scalar(eth_cb.current() == 0 ? "" : eth_cb.get_text())},
            {"config", "WLO", config::yaml_scalar(wl_cb.current() == 0 ? "" : wl_cb.get_text())},
            {"config", "COM_PORT", config::yaml_scalar(com_cb.current() == 0 ? "AUTO" : com_cb.get_text())},
            {"config", "CPU_FAN", config::yaml_scalar(cpu_fan)},
            {"display", "REVISION", revision->second},
            {"display", "DISPLAY_REVERSE", map_key(reverse_map, orient_cb.get_text()).value_or(false) ? "true" : "false"},
            {"display", "BRIGHTNESS", std::to_string(static_cast<int>(brightness_slider.get_value()))},
        });
    } catch (const std::exception &e) {
        show_error(e.what());
        return false;
    }
    return true;
}

void TuringConfigWindow::save_additional_config(const std::string &ping, const std::string &api_key,
                                                const std::string &lat, const std::string &lon,
                                                const std::string &unit, const std::string &lang)
{
    try {
        config::update_yaml_file(main_directory() / "config.yaml", {
            {"config", "PING", config::yaml_scalar(ping)},
            {"config", "WEATHER_API_KEY", config::yaml_scalar(api_key)},
            {"config", "WEATHER_LATITUDE", config::yaml_scalar(lat)},
            {"config", "WEATHER_LONGITUDE", config::yaml_scalar(lon)},
            {"config", "WEATHER_UNITS", config::yaml_scalar(unit)},
            {"config", "WEATHER_LANGUAGE", config::yaml_scalar(lang)},
        });
    } catch (const std::exception &e) {
        show_error(e.what());
    }
}

void TuringConfigWindow::show_error(const std::string &message)
{
    auto dialog = Gtk::AlertDialog::create("Cannot save settings");
    dialog->set_detail(message);
    dialog->show(*this);
}

void TuringConfigWindow::on_theme_change()
{
    load_theme_preview();
}

void TuringConfigWindow::on_open_theme_folder_click()
{
    try {
        Gio::AppInfo::launch_default_for_uri(Glib::filename_to_uri(themes_dir().string()));
    } catch (const Glib::Error &e) {
        logger.error("Cannot open themes folder: {}", e.what());
    }
}

void TuringConfigWindow::on_theme_editor_click()
{
    start_program("theme-editor", {theme_cb.get_text()});
}

void TuringConfigWindow::on_save_click()
{
    save_config_values();
}

void TuringConfigWindow::on_saverun_click()
{
    if (!save_config_values()) {
        return;
    }
    start_program("main");
    close();
}

void TuringConfigWindow::on_brightness_change()
{
    brightness_val_label.set_text(std::to_string(static_cast<int>(brightness_slider.get_value())) + "%");
    show_hide_brightness_warning();
}

void TuringConfigWindow::on_model_change()
{
    show_hide_brightness_warning();
    const bool simulated = model_cb.get_text() == SIMULATED_MODEL;
    com_cb.set_sensitive(!simulated);
    orient_cb.set_sensitive(!simulated);
    brightness_slider.set_sensitive(!simulated);
    brightness_val_label.set_sensitive(!simulated);
}

void TuringConfigWindow::on_size_change()
{
    const std::string size = size_cb.get_text();

    std::vector<std::string> themes;
    if (size == SIZE_2_x_INCH || size == SIZE_2_8_INCH_NEWREV) {
        // For '2.1" / 2.8"' size, search for themes of both sizes
        themes = get_themes(_SIZE_2_1_INCH);
        const auto themes_2_8 = get_themes(_SIZE_2_8_INCH);
        themes.insert(themes.end(), themes_2_8.begin(), themes_2_8.end());
    } else if (size == SIZE_8_8_INCH_NEWREV || size == SIZE_8_8_INCH) {
        // For 8.8" & 9.2" sizes, search for themes of both sizes
        themes = get_themes(SIZE_8_8_INCH);
        const auto themes_9_2 = get_themes(_SIZE_9_2_INCH);
        themes.insert(themes.end(), themes_9_2.begin(), themes_9_2.end());
    } else {
        themes = get_themes(size);
    }

    const std::string current_theme = theme_cb.get_text();
    theme_cb.set_items(themes);

    if (std::find(themes.begin(), themes.end(), current_theme) != themes.end()) {
        theme_cb.set_text(current_theme);
    } else if (!themes.empty()) {
        // The selected theme does not exist anymore / is not allowed for this screen model : select 1st theme avail.
        theme_cb.set_current(0);
    }

    show_hide_brightness_warning();
}

void TuringConfigWindow::on_hwlib_change()
{
    const std::string hwlib = map_key(hw_lib_map, hwlib_cb.get_text()).value_or("AUTO");
    const bool fake = hwlib == "STUB" || hwlib == "STATIC";
    eth_cb.set_sensitive(!fake);
    wl_cb.set_sensitive(!fake);

    const bool python = hwlib == "PYTHON" || hwlib == "AUTO";
    cpu_fan_label.set_visible(python);
    cpu_fan_cb.set_visible(python);
}

void TuringConfigWindow::show_hide_brightness_warning()
{
    // Show warning for Turing Smart screen 3.5 with high brightness
    brightness_warning_label.set_visible(static_cast<int>(brightness_slider.get_value()) > 50 &&
                                         model_cb.get_text() == TURING_MODEL && size_cb.get_text() == SIZE_3_5_INCH);
}

bool TuringConfigWindow::on_fan_speed_update()
{
    // Update fan speed periodically, keeping the selected entry
    const int prev_value = cpu_fan_cb.current();
    const auto fans = get_fans();
    if (fans != cpu_fan_cb.get_items()) {
        cpu_fan_cb.set_items(fans);
        if (prev_value != -1) {
            cpu_fan_cb.set_current(prev_value);
        }
    }
    return true;  // keep the timer
}

// ---------------------------------------------------------------------------------------------------------------------
// MoreConfigWindow

MoreConfigWindow::MoreConfigWindow(TuringConfigWindow &main_window_)
    : main_window(main_window_), unit_cb(map_values(weather_unit_map)), lang_cb(map_values(weather_lang_map))
{
    set_title("Configure weather & ping");
    set_default_size(750, 680);
    set_hide_on_close(true);
    set_child(layout);

    place(layout, *Gtk::make_managed<Gtk::Label>("Hostname / IP to ping"), 10, 10);
    place(layout, ping_entry, 190, 5, 250);

    place(layout, *bold_label("Weather forecast (OpenWeatherMap API)"), 10, 70);

    auto *weather_info_label = Gtk::make_managed<Gtk::Label>(
        "To display weather forecast on themes that support it, you need an OpenWeatherMap \"One Call API 3.0\" key.\n"
        "You will get 1,000 API calls per day for free. This program is configured to stay under this threshold "
        "(~300 calls/day).");
    weather_info_label->set_xalign(0);
    place(layout, *weather_info_label, 10, 100);
    place(layout, *link_label("Click here to subscribe to OpenWeatherMap One Call API 3.0.",
                              "https://openweathermap.org/api"), 10, 140);

    place(layout, *Gtk::make_managed<Gtk::Label>("OpenWeatherMap API key"), 10, 170);
    place(layout, api_entry, 190, 165, 250);

    place(layout, *link_label("You can use online services to get your latitude/longitude e.g. latlong.net (click here)",
                              "https://www.latlong.net/"), 10, 210);

    place(layout, *Gtk::make_managed<Gtk::Label>("Latitude"), 10, 250);
    setup_coordinate_entry(lat_entry, lat_last_valid);
    place(layout, lat_entry, 80, 245, 100);

    place(layout, *Gtk::make_managed<Gtk::Label>("Longitude"), 270, 250);
    setup_coordinate_entry(long_entry, long_last_valid);
    place(layout, long_entry, 340, 245, 100);

    place(layout, *Gtk::make_managed<Gtk::Label>("Units"), 10, 290);
    place(layout, unit_cb, 190, 285, 250);

    place(layout, *Gtk::make_managed<Gtk::Label>("Language"), 10, 330);
    place(layout, lang_cb, 190, 325, 250);

    place(layout, *bold_label("Location search"), 80, 370);

    auto *citysearch2_label = Gtk::make_managed<Gtk::Label>(
        "Enter location to automatically get coordinates (latitude/longitude).\n"
        "For example \"Berlin\" \"London, GB\", \"London, Quebec\".\n"
        "Remember to set valid API key and pick language first!");
    citysearch2_label->set_xalign(0);
    place(layout, *citysearch2_label, 10, 396);

    place(layout, *Gtk::make_managed<Gtk::Label>("Enter location"), 10, 474);
    place(layout, citysearch_entry, 140, 470, 300);
    auto *citysearch_btn = Gtk::make_managed<Gtk::Button>("Search");
    citysearch_btn->signal_clicked().connect(sigc::mem_fun(*this, &MoreConfigWindow::on_search_click));
    place(layout, *citysearch_btn, 450, 468, 130, 40);

    auto *citysearch4_label = Gtk::make_managed<Gtk::Label>("Select location\n(use after Search)");
    citysearch4_label->set_xalign(0);
    place(layout, *citysearch4_label, 10, 540);
    place(layout, citysearch_cb, 140, 544, 360);
    auto *citysearch_btn2 = Gtk::make_managed<Gtk::Button>("Fill in lat/long");
    citysearch_btn2->signal_clicked().connect(sigc::mem_fun(*this, &MoreConfigWindow::on_filllatlong_click));
    place(layout, *citysearch_btn2, 520, 540, 130, 40);

    place(layout, citysearch_warn_label, 20, 600);

    auto *save_btn = Gtk::make_managed<Gtk::Button>("Save settings");
    save_btn->signal_clicked().connect(sigc::mem_fun(*this, &MoreConfigWindow::on_save_click));
    place(layout, *save_btn, 590, 620, 130, 50);
}

void MoreConfigWindow::setup_coordinate_entry(Gtk::Entry &entry, std::string &last_valid)
{
    entry.signal_changed().connect([&entry, &last_valid] {
        const std::string text = entry.get_text();
        bool valid = text.empty() || text == "-" || text == "." || text == "-.";  // partial input
        if (!valid) {
            try {
                size_t pos;
                std::stod(text, &pos);
                valid = pos == text.size();
            } catch (const std::exception &) {
                valid = false;
            }
        }
        if (valid) {
            last_valid = text;
        } else {
            const int position = entry.get_position();
            entry.set_text(last_valid);
            entry.set_position(std::max(0, position - 1));
        }
    });
}

void MoreConfigWindow::show_window()
{
    present();
}

void MoreConfigWindow::load_config_values(const YAML::Node &cfg)
{
    const YAML::Node &c = cfg;
    const YAML::Node conf = c["config"];
    ping_entry.set_text(config::get(conf, "PING", "8.8.8.8"));
    api_entry.set_text(config::get(conf, "WEATHER_API_KEY", ""));
    lat_entry.set_text(config::get(conf, "WEATHER_LATITUDE", "45.75"));
    long_entry.set_text(config::get(conf, "WEATHER_LONGITUDE", "45.75"));
    if (const auto unit = map_value(weather_unit_map, config::get(conf, "WEATHER_UNITS", "metric"))) {
        unit_cb.set_text(*unit);
    } else {
        unit_cb.set_current(0);
    }
    lang_cb.set_text(map_value(weather_lang_map, config::get(conf, "WEATHER_LANGUAGE", "en"))
                         .value_or(*map_value(weather_lang_map, std::string("en"))));
}

void MoreConfigWindow::citysearch_show_warning(const std::string &warning)
{
    citysearch_warn_label.set_markup("<span foreground=\"" + RED_TEXT_COLOR + "\">" +
                                     Glib::Markup::escape_text(warning) + "</span>");
}

void MoreConfigWindow::on_search_click()
{
    const std::string OPENWEATHER_GEOAPI_URL = "http://api.openweathermap.org/geo/1.0/direct";
    const std::string api_key = api_entry.get_text();
    const std::string lang = map_key(weather_lang_map, lang_cb.get_text()).value_or("en");
    const std::string city = citysearch_entry.get_text();

    if (api_key.empty() || city.empty()) {
        citysearch_show_warning("API key and city name cannot be empty.");
        return;
    }

    CURL *curl = curl_easy_init();
    if (!curl) {
        citysearch_show_warning("Error fetching OpenWeatherMap Geo API");
        return;
    }
    auto escape = [curl](const std::string &value) {
        char *escaped = curl_easy_escape(curl, value.c_str(), static_cast<int>(value.size()));
        std::string result = escaped ? escaped : "";
        curl_free(escaped);
        return result;
    };
    const std::string url = OPENWEATHER_GEOAPI_URL + "?appid=" + escape(api_key) + "&lang=" + escape(lang) +
                            "&q=" + escape(city) + "&limit=10";
    std::string body;
    long status_code = 0;
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &body);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 5L);
    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
    const CURLcode res = curl_easy_perform(curl);
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status_code);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK) {
        citysearch_show_warning("Error fetching OpenWeatherMap Geo API");
        return;
    }
    if (status_code == 401) {
        citysearch_show_warning("Invalid OpenWeatherMap API key.");
        return;
    } else if (status_code != 200) {
        citysearch_show_warning(std::format("Error #{} fetching OpenWeatherMap Geo API.", status_code));
        return;
    }

    city_entries.clear();
    std::vector<std::string> cb_entries;
    try {
        // JSON is parsed with the YAML parser (JSON is a subset of YAML)
        const YAML::Node data = YAML::Load(body);
        // Country names in the selected language, e.g. "zh_cn" -> zh_CN
        std::string locale_name = lang;
        if (const auto underscore = locale_name.find('_'); underscore != std::string::npos) {
            for (size_t i = underscore + 1; i < locale_name.size(); i++) {
                locale_name[i] = static_cast<char>(std::toupper(static_cast<unsigned char>(locale_name[i])));
            }
        }
        const icu::Locale display_locale(locale_name.c_str());
        for (const auto &entry: data) {
            const std::string name = entry["name"].as<std::string>();
            const std::string state = config::get(entry, "state", "");
            const std::string lat = entry["lat"].as<std::string>();
            const std::string lon = entry["lon"].as<std::string>();
            std::string country_code = entry["country"].as<std::string>();
            for (auto &ch: country_code) {
                ch = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
            }
            icu::UnicodeString country_name;
            icu::Locale(("und_" + country_code).c_str()).getDisplayCountry(display_locale, country_name);
            std::string country;
            country_name.toUTF8String(country);
            if (country.empty()) {
                country = country_code;
            }
            const std::string full_name = state.empty() ? std::format("{}, {}", name, country)
                                                        : std::format("{}, {}, {}", name, state, country);
            city_entries.push_back({full_name, lat, lon});
            cb_entries.push_back(full_name);
        }
    } catch (const YAML::Exception &) {
        citysearch_show_warning("Error fetching OpenWeatherMap Geo API");
        return;
    }

    citysearch_cb.set_items(cb_entries);
    if (cb_entries.empty()) {
        citysearch_show_warning("No given city found.");
    } else {
        citysearch_cb.set_current(0);
        citysearch_show_warning("Select your city now from list and apply \"Fill in lat/long\".");
    }
}

void MoreConfigWindow::on_filllatlong_click()
{
    const std::string selected = citysearch_cb.get_text();
    const auto city = std::find_if(city_entries.begin(), city_entries.end(),
                                   [&](const CityEntry &c) { return c.full_name == selected; });
    if (city_entries.empty() || city == city_entries.end()) {
        citysearch_show_warning("No city selected or no search results.");
        return;
    }
    lat_entry.set_text(city->lat);
    long_entry.set_text(city->lon);
    citysearch_show_warning("Lat/long values filled for " + city->full_name);
}

void MoreConfigWindow::on_save_click()
{
    save_config_values();
    set_visible(false);
}

void MoreConfigWindow::save_config_values()
{
    main_window.save_additional_config(ping_entry.get_text(), api_entry.get_text(), lat_entry.get_text(),
                                       long_entry.get_text(),
                                       map_key(weather_unit_map, unit_cb.get_text()).value_or("metric"),
                                       map_key(weather_lang_map, lang_cb.get_text()).value_or("en"));
}

int main(int argc, char *argv[])
{
    curl_global_init(CURL_GLOBAL_DEFAULT);
    auto app = Gtk::Application::create("io.github.turing_smart_screen.Configure");
    return app->make_window_and_run<TuringConfigWindow>(argc, argv);
}
