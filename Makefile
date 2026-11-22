# SPDX-License-Identifier: GPL-3.0-or-later
#
# turing-smart-screen - C++ port of turing-smart-screen-python, a system monitor and library for USB-C displays
# https://github.com/mathoudebine/turing-smart-screen-python/
#
# Build system for the C++ port (target platform: Ubuntu 26.04 LTS).
#
#   make              build every program into build/bin/
#   make main         build only the system monitor (main.py)
#   make configure    build only the configuration GUI (configure.py)
#   make test         build and run the unit tests
#   make deps         check that all build dependencies are installed
#   make clean        remove build/
#   make DEBUG=1      build without optimizations, with debug symbols
#
# CPPFLAGS, CXXFLAGS, LDFLAGS and LDLIBS given on the command line are added to the project flags, e.g.:
#   make CXXFLAGS=-fsanitize=address LDFLAGS=-fsanitize=address
#
# Build dependencies (Ubuntu packages):
#   build-essential pkg-config libyaml-cpp-dev libfreetype-dev libharfbuzz-dev libpng-dev libjpeg-dev
#   libusb-1.0-0-dev libcurl4-openssl-dev libicu-dev libgtkmm-4.0-dev libgtest-dev

CXX      ?= g++
CXXSTD   := -std=c++20
WARNINGS := -Wall -Wextra -Wpedantic

ifeq ($(DEBUG),1)
  OPTFLAGS := -O0 -g
else
  OPTFLAGS := -O2
endif

SRC_DIR   := src
TEST_DIR  := tests/cpp
BUILD_DIR := build
OBJ_DIR   := $(BUILD_DIR)/obj
BIN_DIR   := $(BUILD_DIR)/bin

# pkg-config modules, grouped by what links them
LIB_PKGS  := yaml-cpp freetype2 harfbuzz libpng libjpeg libusb-1.0 libcurl icu-uc icu-i18n
GUI_PKGS  := gtkmm-4.0
TEST_PKGS := gtest gtest_main

PKG_CONFIG ?= pkg-config
# Dependencies headers are included as system headers: their warnings are not reported
LIB_CFLAGS  := $(patsubst -I%,-isystem %,$(shell $(PKG_CONFIG) --cflags $(LIB_PKGS) 2>/dev/null))
LIB_LIBS    := $(shell $(PKG_CONFIG) --libs $(LIB_PKGS) 2>/dev/null)
GUI_CFLAGS  := $(patsubst -I%,-isystem %,$(shell $(PKG_CONFIG) --cflags $(GUI_PKGS) 2>/dev/null))
GUI_LIBS    := $(shell $(PKG_CONFIG) --libs $(GUI_PKGS) 2>/dev/null)
TEST_CFLAGS := $(patsubst -I%,-isystem %,$(shell $(PKG_CONFIG) --cflags $(TEST_PKGS) 2>/dev/null))
TEST_LIBS   := $(shell $(PKG_CONFIG) --libs $(TEST_PKGS) 2>/dev/null)

ALL_CPPFLAGS = -I$(SRC_DIR) -MMD -MP $(CPPFLAGS)
ALL_CXXFLAGS = $(CXXSTD) $(WARNINGS) $(OPTFLAGS) $(LIB_CFLAGS) $(CXXFLAGS)
ALL_LDLIBS   = $(LDLIBS) $(LIB_LIBS) -pthread

# Shared library code (library/ in Python), linked into every program
LIB_SRCS := $(shell find $(SRC_DIR)/library -name '*.cpp' 2>/dev/null)
LIB_OBJS := $(LIB_SRCS:$(SRC_DIR)/%.cpp=$(OBJ_DIR)/%.o)
LIB_A    := $(BUILD_DIR)/libturing.a

# Programs: one entry point per Python application file
MAIN_OBJS           := $(OBJ_DIR)/main.o
CONFIGURE_OBJS      := $(OBJ_DIR)/configure.o
THEME_EDITOR_OBJS   := $(OBJ_DIR)/theme-editor.o
SIMPLE_PROGRAM_OBJS := $(OBJ_DIR)/simple-program.o

PROGRAMS := $(BIN_DIR)/main $(BIN_DIR)/configure $(BIN_DIR)/theme-editor $(BIN_DIR)/simple-program

# Unit tests (tests/ in Python)
TEST_SRCS := $(shell find $(TEST_DIR) -name '*.cpp' 2>/dev/null)
TEST_OBJS := $(TEST_SRCS:$(TEST_DIR)/%.cpp=$(OBJ_DIR)/tests/%.o)
TEST_BIN  := $(BIN_DIR)/unit-tests

.PHONY: all main configure theme-editor simple-program test deps clean

all: $(PROGRAMS)

main: $(BIN_DIR)/main
configure: $(BIN_DIR)/configure
theme-editor: $(BIN_DIR)/theme-editor
simple-program: $(BIN_DIR)/simple-program

$(LIB_A): $(LIB_OBJS)
	@mkdir -p $(@D)
	$(AR) rcs $@ $^

$(BIN_DIR)/main: $(MAIN_OBJS) $(LIB_A)
	@mkdir -p $(@D)
	$(CXX) $(LDFLAGS) -o $@ $^ $(ALL_LDLIBS)

$(BIN_DIR)/simple-program: $(SIMPLE_PROGRAM_OBJS) $(LIB_A)
	@mkdir -p $(@D)
	$(CXX) $(LDFLAGS) -o $@ $^ $(ALL_LDLIBS)

$(BIN_DIR)/configure: $(CONFIGURE_OBJS) $(LIB_A)
	@mkdir -p $(@D)
	$(CXX) $(LDFLAGS) -o $@ $^ $(GUI_LIBS) $(ALL_LDLIBS)

$(BIN_DIR)/theme-editor: $(THEME_EDITOR_OBJS) $(LIB_A)
	@mkdir -p $(@D)
	$(CXX) $(LDFLAGS) -o $@ $^ $(GUI_LIBS) $(ALL_LDLIBS)

# GUI programs need the gtkmm include paths
$(CONFIGURE_OBJS) $(THEME_EDITOR_OBJS): ALL_CXXFLAGS += $(GUI_CFLAGS)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp
	@mkdir -p $(@D)
	$(CXX) $(ALL_CPPFLAGS) $(ALL_CXXFLAGS) -c -o $@ $<

# Tests
$(OBJ_DIR)/tests/%.o: $(TEST_DIR)/%.cpp
	@mkdir -p $(@D)
	$(CXX) $(ALL_CPPFLAGS) $(ALL_CXXFLAGS) $(TEST_CFLAGS) -c -o $@ $<

$(TEST_BIN): $(TEST_OBJS) $(LIB_A)
	@mkdir -p $(@D)
	$(CXX) $(LDFLAGS) -o $@ $^ $(TEST_LIBS) $(ALL_LDLIBS)

test:
ifeq ($(strip $(TEST_SRCS)),)
	@echo "No C++ unit tests yet in $(TEST_DIR)/"
else
	@$(MAKE) --no-print-directory $(TEST_BIN)
	$(TEST_BIN)
endif

deps:
	@missing=0; \
	for pkg in $(LIB_PKGS) $(GUI_PKGS) $(TEST_PKGS); do \
		if $(PKG_CONFIG) --exists $$pkg; then \
			printf "  %-12s %s\n" $$pkg "$$($(PKG_CONFIG) --modversion $$pkg)"; \
		else \
			printf "  %-12s MISSING\n" $$pkg; missing=1; \
		fi; \
	done; \
	if [ $$missing -eq 1 ]; then \
		echo "Install them with: sudo apt install build-essential pkg-config libyaml-cpp-dev libfreetype-dev libharfbuzz-dev \
libpng-dev libjpeg-dev libusb-1.0-0-dev libcurl4-openssl-dev libicu-dev libgtkmm-4.0-dev libgtest-dev"; \
		exit 1; \
	fi

clean:
	rm -rf $(BUILD_DIR)

-include $(shell find $(OBJ_DIR) -name '*.d' 2>/dev/null)
