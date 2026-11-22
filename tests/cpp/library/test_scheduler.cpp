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

// Unit tests of library/scheduler (C++ port of library/scheduler.py)

#include <atomic>
#include <chrono>
#include <stdexcept>
#include <thread>

#include <gtest/gtest.h>

#include "library/scheduler.h"

TEST(Scheduler, PeriodicJobAndStop)
{
    std::atomic<int> runs = 0;
    std::atomic<int> failing_runs = 0;
    scheduler::schedule("test_job", 0.05, [&] { runs++; });
    // A job throwing an exception keeps running
    scheduler::schedule("test_failing", 0.05, [&] {
        failing_runs++;
        throw std::runtime_error("test error");
    });
    // Interval 0: job not started
    scheduler::schedule("test_disabled", 0, [] { FAIL() << "disabled job must not run"; });

    std::this_thread::sleep_for(std::chrono::milliseconds(280));
    EXPECT_GE(runs, 4);
    EXPECT_LE(runs, 7);
    EXPECT_GE(failing_runs, 4);

    scheduler::stop();
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    const int runs_after_stop = runs;
    std::this_thread::sleep_for(std::chrono::milliseconds(150));
    EXPECT_EQ(runs, runs_after_stop);
}
