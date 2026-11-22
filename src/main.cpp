// SPDX-License-Identifier: GPL-3.0-or-later
//
// turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
// https://github.com/mathoudebine/turing-smart-screen-python/
//
// Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
// Copyright (C) 2022 Rollbacke
// Copyright (C) 2022 Ebag333
// Copyright (C) 2022 w1ld3r
// Copyright (C) 2022 Charles Ferguson (gerph)
// Copyright (C) 2022 Russ Nelson (RussNelson)
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

// C++ port of main.py: the system monitor main program, displaying HW sensors on the screen using themes.

#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <iostream>
#include <optional>
#include <string>
#include <thread>

#include <filesystem>
#include <memory>

#include <pthread.h>
#include <spawn.h>
#include <unistd.h>

#include "library/config.h"
#include "library/display.h"
#include "library/log.h"
#include "library/scheduler.h"
#include "library/stats.h"
#include "library/tray_icon.h"

extern char **environ;

namespace {

constexpr auto DELAY_BETWEEN_THREADS = std::chrono::milliseconds(250);

// Signal sent to this process by the tray icon menu to stop the program (handled like the other stopping signals)
constexpr int STOP_FROM_TRAY_SIGNAL = SIGUSR1;

std::unique_ptr<TrayIcon> tray_icon;

// Directory containing this program (build/bin/)
std::filesystem::path program_directory()
{
    std::error_code ec;
    const std::filesystem::path exe = std::filesystem::read_symlink("/proc/self/exe", ec);
    return ec ? std::filesystem::current_path() : exe.parent_path();
}

void wait_for_empty_queue(int timeout = 5)
{
    // Waiting for all pending request to be sent to display
    logger.info("Waiting for all pending request to be sent to display ({}s max)...", timeout);

    double wait_time = 0;
    while (!scheduler::is_queue_empty() && wait_time < timeout) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        wait_time = wait_time + 0.1;
    }

    logger.debug("(Waited {:.1f}s)", wait_time);
}

[[noreturn]] void clean_stop()
{
    // Turn screen and LEDs off before stopping
    display().turn_off();

    // Do not stop the program now in case data transmission was in progress
    // Instead, ask the scheduler to empty the action queue before stopping
    scheduler::stop();

    // Waiting for all pending request to be sent to display
    wait_for_empty_queue(5);

    // Remove tray icon just before exit
    if (tray_icon) {
        tray_icon->stop();
    }

    // We force the exit to avoid waiting for other scheduled tasks: they may be in a long blocking call!
    std::_Exit(0);
}

void on_configure_tray()
{
    logger.info("Configure from tray icon");

    // Start the configuration program, built in the same directory. The stopping signals are blocked in this
    // program: they must not be blocked in the new process.
    const std::string configure_file = (program_directory() / "configure").string();
    posix_spawnattr_t attr;
    posix_spawnattr_init(&attr);
    sigset_t no_signals;
    sigemptyset(&no_signals);
    posix_spawnattr_setsigmask(&attr, &no_signals);
    posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETSIGMASK);
    char *const spawn_argv[] = {const_cast<char *>(configure_file.c_str()), nullptr};
    pid_t pid;
    const int ret = posix_spawn(&pid, configure_file.c_str(), nullptr, &attr, spawn_argv, environ);
    posix_spawnattr_destroy(&attr);
    if (ret != 0) {
        logger.error("Cannot start {}: {}", configure_file, std::strerror(ret));
    }

    kill(getpid(), STOP_FROM_TRAY_SIGNAL);
}

void on_exit_tray()
{
    logger.info("Exit from tray icon");
    kill(getpid(), STOP_FROM_TRAY_SIGNAL);
}

void print_usage(const char *program)
{
    std::cout << "usage: " << program << " [-h] [-t THEME_SCREENSHOTS]\n\n"
              << "Turing System Monitor\n\n"
              << "options:\n"
              << "  -h, --help            show this help message and exit\n"
              << "  -t, --theme-screenshots THEME_SCREENSHOTS\n"
              << "                        Run n iterations in automated mode to generate themes screenshots.\n";
}

// Parse command-line arguments. Returns the number of theme screenshots iterations, if any. Exits on error.
std::optional<int> parse_arguments(int argc, char *argv[])
{
    std::optional<int> theme_screenshots;
    for (int i = 1; i < argc; i++) {
        const std::string arg = argv[i];
        std::string value;
        if (arg == "-h" || arg == "--help") {
            print_usage(argv[0]);
            std::exit(0);
        } else if (arg == "-t" || arg == "--theme-screenshots") {
            if (i + 1 >= argc) {
                std::cerr << argv[0] << ": error: argument -t/--theme-screenshots: expected one argument\n";
                std::exit(2);
            }
            value = argv[++i];
        } else if (arg.rfind("--theme-screenshots=", 0) == 0) {
            value = arg.substr(std::strlen("--theme-screenshots="));
        } else {
            print_usage(argv[0]);
            std::cerr << argv[0] << ": error: unrecognized arguments: " << arg << "\n";
            std::exit(2);
        }
        try {
            size_t pos;
            theme_screenshots = std::stoi(value, &pos);
            if (pos != value.size()) {
                throw std::invalid_argument(value);
            }
        } catch (const std::exception &) {
            std::cerr << argv[0] << ": error: argument -t/--theme-screenshots: invalid int value: '" << value
                      << "'\n";
            std::exit(2);
        }
    }
    return theme_screenshots;
}

}  // namespace

int main(int argc, char *argv[])
{
    // Parse command-line arguments
    const std::optional<int> theme_screenshots = parse_arguments(argc, argv);

    // The stopping signals are handled by the main thread (sigwait below), to send a complete frame to the LCD before
    // exit: they are blocked in all threads, including the threads created later that inherit this mask
    sigset_t stop_signals;
    sigemptyset(&stop_signals);
    sigaddset(&stop_signals, SIGINT);
    sigaddset(&stop_signals, SIGTERM);
    sigaddset(&stop_signals, SIGQUIT);
    sigaddset(&stop_signals, STOP_FROM_TRAY_SIGNAL);
    pthread_sigmask(SIG_BLOCK, &stop_signals, nullptr);

    // Create a tray icon for the program, with Configure and Exit entries in menu
    std::vector<std::string> icon_paths;
    for (const char *size: {"24", "32", "48", "64", "128"}) {
        icon_paths.push_back((config::find_main_directory() / "res/icons/monitor-icon-17865" / (std::string(size) + ".png")).string());
    }
    tray_icon = std::make_unique<TrayIcon>("Turing System Monitor", "Turing System Monitor", icon_paths,
                                           std::vector<TrayIcon::MenuItem>{
                                               {"Configure", on_configure_tray},
                                               {"", nullptr},  // separator
                                               {"Exit", on_exit_tray},
                                           });
    if (!tray_icon->run_detached()) {
        tray_icon.reset();
    }

    try {
        // Load config.yaml and the theme
        config::init();

        // Initialize the display
        logger.info("Initialize display");
        display().initialize_display();

        // Start serial queue handler
        if (!theme_screenshots) {
            scheduler::QueueHandler();
        }

        // Create all static images
        display().display_static_images();

        // Create all static texts
        display().display_static_text();

        // Wait for static images/text to be displayed before starting monitoring (to avoid filling the queue while
        // waiting)
        if (!theme_screenshots) {
            wait_for_empty_queue(10);
        }

        // Start sensor scheduled reading. Avoid starting them all at the same time to optimize load
        logger.info("Starting system monitoring");
        stats::init();

        if (!theme_screenshots) {
            scheduler::CPUPercentage(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::CPUFrequency(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::CPULoad(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::CPUTemperature(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::CPUFanSpeed(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            if (stats::Gpu::is_available()) {
                scheduler::GpuStats(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            }
            scheduler::MemoryStats(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::DiskStats(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::NetStats(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::DateStats(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::SystemUptimeStats(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::CustomStats(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::WeatherStats(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
            scheduler::PingStats(); std::this_thread::sleep_for(DELAY_BETWEEN_THREADS);
        } else {
            logger.info("Theme screenshots mode enabled - program will run {} iterations then close.",
                        *theme_screenshots);
            // Run a predefined number of time to generate theme screenshot then close
            for (int i = 0; i < *theme_screenshots; i++) {
                logger.debug("Iteration #{}", i);
                stats::CPU::percentage();
                stats::CPU::frequency();
                stats::CPU::load();
                stats::CPU::temperature();
                stats::CPU::fan_speed();
                stats::Gpu::stats();
                stats::Memory::stats();
                stats::Disk::stats();
                stats::Net::stats();
                stats::Date::stats();
                stats::SystemUptime::stats();
                stats::Custom::stats();
                stats::Weather::stats();
                stats::Ping::stats();
            }
            logger.debug("Finished theme generation, program will close.");
            clean_stop();
        }
    } catch (const std::exception &e) {
        logger.error("{}", e.what());
        return 1;
    }

    // Wait for a stopping signal (Ctrl+C, kill...), then stop cleanly
    int signum = 0;
    sigwait(&stop_signals, &signum);
    if (signum != STOP_FROM_TRAY_SIGNAL) {
        logger.info("Caught signal {}, exiting", signum);
    }
    clean_stop();
}
