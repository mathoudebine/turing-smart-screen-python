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

// System tray icon with a menu (StatusNotifierItem + com.canonical.dbusmenu over D-Bus), replacing pystray.

#include "library/tray_icon.h"

#include <future>
#include <map>
#include <optional>
#include <unistd.h>

#include <gio/gio.h>
#include <png.h>

#include "library/log.h"

namespace {

constexpr const char *ITEM_PATH = "/StatusNotifierItem";
constexpr const char *MENU_PATH = "/MenuBar";
constexpr const char *WATCHER_NAME = "org.kde.StatusNotifierWatcher";
constexpr guint32 MENU_REVISION = 1;

constexpr const char *INTROSPECTION_XML = R"XML(
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="i" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="OverlayIconName" type="s" access="read"/>
    <property name="OverlayIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="AttentionIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionMovieName" type="s" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <method name="ContextMenu"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
    <method name="Activate"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
    <method name="SecondaryActivate"><arg name="x" type="i" direction="in"/><arg name="y" type="i" direction="in"/></method>
    <method name="Scroll"><arg name="delta" type="i" direction="in"/><arg name="orientation" type="s" direction="in"/></method>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewStatus"><arg name="status" type="s"/></signal>
    <signal name="NewToolTip"/>
  </interface>
  <interface name="com.canonical.dbusmenu">
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
    <method name="GetLayout">
      <arg name="parentId" type="i" direction="in"/>
      <arg name="recursionDepth" type="i" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="revision" type="u" direction="out"/>
      <arg name="layout" type="(ia{sv}av)" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="properties" type="a(ia{sv})" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg name="id" type="i" direction="in"/>
      <arg name="name" type="s" direction="in"/>
      <arg name="value" type="v" direction="out"/>
    </method>
    <method name="Event">
      <arg name="id" type="i" direction="in"/>
      <arg name="eventId" type="s" direction="in"/>
      <arg name="data" type="v" direction="in"/>
      <arg name="timestamp" type="u" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg name="events" type="a(isvu)" direction="in"/>
      <arg name="idErrors" type="ai" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg name="id" type="i" direction="in"/>
      <arg name="needUpdate" type="b" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="updatesNeeded" type="ai" direction="out"/>
      <arg name="idErrors" type="ai" direction="out"/>
    </method>
    <signal name="ItemsPropertiesUpdated">
      <arg name="updatedProps" type="a(ia{sv})"/>
      <arg name="removedProps" type="a(ias)"/>
    </signal>
    <signal name="LayoutUpdated"><arg name="revision" type="u"/><arg name="parent" type="i"/></signal>
    <signal name="ItemActivationRequested"><arg name="id" type="i"/><arg name="timestamp" type="u"/></signal>
  </interface>
</node>
)XML";

struct Pixmap
{
    int width;
    int height;
    std::vector<uint8_t> argb;  // ARGB32 in network byte order
};

std::optional<Pixmap> load_pixmap(const std::string &path)
{
    png_image png{};
    png.version = PNG_IMAGE_VERSION;
    if (!png_image_begin_read_from_file(&png, path.c_str())) {
        return std::nullopt;
    }
    png.format = PNG_FORMAT_ARGB;
    Pixmap pixmap{static_cast<int>(png.width), static_cast<int>(png.height), std::vector<uint8_t>(PNG_IMAGE_SIZE(png))};
    if (!png_image_finish_read(&png, nullptr, pixmap.argb.data(), 0, nullptr)) {
        png_image_free(&png);
        return std::nullopt;
    }
    return pixmap;
}

GVariant *empty_pixmaps()
{
    return g_variant_new_array(G_VARIANT_TYPE("(iiay)"), nullptr, 0);
}

}  // namespace

struct TrayIcon::Private
{
    std::string name;
    std::string title;
    std::vector<Pixmap> pixmaps;
    std::vector<MenuItem> menu;

    GMainContext *context = nullptr;
    GMainLoop *loop = nullptr;
    GDBusConnection *connection = nullptr;
    GDBusNodeInfo *node_info = nullptr;
    guint item_registration = 0, menu_registration = 0, own_id = 0, watch_id = 0;
    std::string bus_name;
    bool watcher_seen = false;
    bool watcher_warning_done = false;

    // ---- StatusNotifierItem

    GVariant *pixmaps_variant() const
    {
        GVariantBuilder builder;
        g_variant_builder_init(&builder, G_VARIANT_TYPE("a(iiay)"));
        for (const auto &pixmap: pixmaps) {
            GVariant *bytes = g_variant_new_fixed_array(G_VARIANT_TYPE_BYTE, pixmap.argb.data(), pixmap.argb.size(), 1);
            g_variant_builder_add(&builder, "(ii@ay)", pixmap.width, pixmap.height, bytes);
        }
        return g_variant_builder_end(&builder);
    }

    GVariant *item_property(const std::string &property) const
    {
        if (property == "Category") return g_variant_new_string("ApplicationStatus");
        if (property == "Id") return g_variant_new_string(name.c_str());
        if (property == "Title") return g_variant_new_string(title.c_str());
        if (property == "Status") return g_variant_new_string("Active");
        if (property == "WindowId") return g_variant_new_int32(0);
        if (property == "IconThemePath" || property == "IconName" || property == "OverlayIconName" ||
            property == "AttentionIconName" || property == "AttentionMovieName") {
            return g_variant_new_string("");
        }
        if (property == "IconPixmap") return pixmaps_variant();
        if (property == "OverlayIconPixmap" || property == "AttentionIconPixmap") return empty_pixmaps();
        if (property == "ToolTip") return g_variant_new("(s@a(iiay)ss)", "", empty_pixmaps(), title.c_str(), "");
        if (property == "ItemIsMenu") return g_variant_new_boolean(TRUE);
        if (property == "Menu") return g_variant_new_object_path(MENU_PATH);
        return nullptr;
    }

    // ---- com.canonical.dbusmenu: root item 0, menu items 1..n

    GVariant *menu_item_properties(int id) const
    {
        GVariantBuilder builder;
        g_variant_builder_init(&builder, G_VARIANT_TYPE("a{sv}"));
        if (id == 0) {
            g_variant_builder_add(&builder, "{sv}", "children-display", g_variant_new_string("submenu"));
        } else {
            const MenuItem &item = menu[static_cast<size_t>(id - 1)];
            if (item.label.empty()) {
                g_variant_builder_add(&builder, "{sv}", "type", g_variant_new_string("separator"));
            } else {
                g_variant_builder_add(&builder, "{sv}", "label", g_variant_new_string(item.label.c_str()));
                g_variant_builder_add(&builder, "{sv}", "enabled", g_variant_new_boolean(TRUE));
            }
            g_variant_builder_add(&builder, "{sv}", "visible", g_variant_new_boolean(TRUE));
        }
        return g_variant_builder_end(&builder);
    }

    bool valid_menu_id(int id) const { return id >= 0 && id <= static_cast<int>(menu.size()); }

    GVariant *menu_layout(int id) const
    {
        GVariantBuilder children;
        g_variant_builder_init(&children, G_VARIANT_TYPE("av"));
        if (id == 0) {
            for (int child = 1; child <= static_cast<int>(menu.size()); child++) {
                g_variant_builder_add(&children, "v", menu_layout(child));
            }
        }
        return g_variant_new("(i@a{sv}@av)", id, menu_item_properties(id), g_variant_builder_end(&children));
    }

    GVariant *menu_property(const std::string &property) const
    {
        if (property == "Version") return g_variant_new_uint32(3);
        if (property == "TextDirection") return g_variant_new_string("ltr");
        if (property == "Status") return g_variant_new_string("normal");
        if (property == "IconThemePath") return g_variant_new_strv(nullptr, 0);
        return nullptr;
    }

    void menu_event(int id, const std::string &event_id) const
    {
        if (event_id == "clicked" && id > 0 && valid_menu_id(id)) {
            const MenuItem &item = menu[static_cast<size_t>(id - 1)];
            if (item.action) {
                item.action();
            }
        }
    }

    void menu_method(const std::string &method, GVariant *parameters, GDBusMethodInvocation *invocation) const
    {
        if (method == "GetLayout") {
            gint32 parent_id, depth;
            g_variant_get(parameters, "(ii^a&s)", &parent_id, &depth, nullptr);
            if (!valid_menu_id(parent_id)) {
                g_dbus_method_invocation_return_dbus_error(invocation, "com.canonical.dbusmenu.Error", "Invalid id");
                return;
            }
            g_dbus_method_invocation_return_value(invocation,
                                                  g_variant_new("(u@(ia{sv}av))", MENU_REVISION, menu_layout(parent_id)));
        } else if (method == "GetGroupProperties") {
            GVariant *ids = g_variant_get_child_value(parameters, 0);
            GVariantBuilder builder;
            g_variant_builder_init(&builder, G_VARIANT_TYPE("a(ia{sv})"));
            const gsize count = g_variant_n_children(ids);
            if (count == 0) {
                for (int id = 0; id <= static_cast<int>(menu.size()); id++) {
                    g_variant_builder_add(&builder, "(i@a{sv})", id, menu_item_properties(id));
                }
            }
            for (gsize i = 0; i < count; i++) {
                gint32 id;
                g_variant_get_child(ids, i, "i", &id);
                if (valid_menu_id(id)) {
                    g_variant_builder_add(&builder, "(i@a{sv})", id, menu_item_properties(id));
                }
            }
            g_variant_unref(ids);
            g_dbus_method_invocation_return_value(invocation, g_variant_new("(@a(ia{sv}))", g_variant_builder_end(&builder)));
        } else if (method == "GetProperty") {
            gint32 id;
            const gchar *name_property;
            g_variant_get(parameters, "(i&s)", &id, &name_property);
            GVariant *value = nullptr;
            if (valid_menu_id(id)) {
                GVariant *properties = menu_item_properties(id);
                value = g_variant_lookup_value(properties, name_property, nullptr);
                g_variant_unref(g_variant_ref_sink(properties));
            }
            if (!value) {
                g_dbus_method_invocation_return_dbus_error(invocation, "com.canonical.dbusmenu.Error", "Unknown property");
                return;
            }
            g_dbus_method_invocation_return_value(invocation, g_variant_new("(v)", value));
            g_variant_unref(value);
        } else if (method == "Event") {
            gint32 id;
            const gchar *event_id;
            g_variant_get(parameters, "(i&svu)", &id, &event_id, nullptr, nullptr);
            const std::string event = event_id;
            g_dbus_method_invocation_return_value(invocation, nullptr);
            menu_event(id, event);
        } else if (method == "EventGroup") {
            GVariant *events = g_variant_get_child_value(parameters, 0);
            std::vector<std::pair<int, std::string>> to_run;
            for (gsize i = 0; i < g_variant_n_children(events); i++) {
                gint32 id;
                const gchar *event_id;
                g_variant_get_child(events, i, "(i&svu)", &id, &event_id, nullptr, nullptr);
                to_run.emplace_back(id, event_id);
            }
            g_variant_unref(events);
            g_dbus_method_invocation_return_value(invocation, g_variant_new("(@ai)", g_variant_new_array(G_VARIANT_TYPE_INT32, nullptr, 0)));
            for (const auto &[id, event]: to_run) {
                menu_event(id, event);
            }
        } else if (method == "AboutToShow") {
            g_dbus_method_invocation_return_value(invocation, g_variant_new("(b)", FALSE));
        } else if (method == "AboutToShowGroup") {
            g_dbus_method_invocation_return_value(
                invocation, g_variant_new("(@ai@ai)", g_variant_new_array(G_VARIANT_TYPE_INT32, nullptr, 0),
                                          g_variant_new_array(G_VARIANT_TYPE_INT32, nullptr, 0)));
        } else {
            g_dbus_method_invocation_return_dbus_error(invocation, "org.freedesktop.DBus.Error.UnknownMethod", method.c_str());
        }
    }

    // ---- registration with the StatusNotifierWatcher of the desktop

    void register_with_watcher()
    {
        g_dbus_connection_call(
            connection, WATCHER_NAME, "/StatusNotifierWatcher", WATCHER_NAME, "RegisterStatusNotifierItem",
            g_variant_new("(s)", bus_name.c_str()), nullptr, G_DBUS_CALL_FLAGS_NONE, -1, nullptr,
            [](GObject *source, GAsyncResult *result, gpointer) {
                GError *error = nullptr;
                GVariant *reply = g_dbus_connection_call_finish(G_DBUS_CONNECTION(source), result, &error);
                if (reply) {
                    logger.info("Tray icon has been displayed");
                    g_variant_unref(reply);
                } else {
                    logger.warning("Tray icon could not be registered: {}", error->message);
                    g_error_free(error);
                }
            },
            nullptr);
    }
};

namespace {

void item_method_call(GDBusConnection *, const gchar *, const gchar *, const gchar *interface_name,
                      const gchar *method_name, GVariant *parameters, GDBusMethodInvocation *invocation,
                      gpointer user_data)
{
    auto *d = static_cast<TrayIcon::Private *>(user_data);
    if (g_strcmp0(interface_name, "com.canonical.dbusmenu") == 0) {
        d->menu_method(method_name, parameters, invocation);
    } else {
        // ContextMenu, Activate, SecondaryActivate, Scroll: nothing to do, the host displays the menu (ItemIsMenu)
        g_dbus_method_invocation_return_value(invocation, nullptr);
    }
}

GVariant *item_get_property(GDBusConnection *, const gchar *, const gchar *, const gchar *interface_name,
                            const gchar *property_name, GError **error, gpointer user_data)
{
    auto *d = static_cast<TrayIcon::Private *>(user_data);
    GVariant *value = g_strcmp0(interface_name, "com.canonical.dbusmenu") == 0 ? d->menu_property(property_name)
                                                                                : d->item_property(property_name);
    if (!value) {
        g_set_error(error, G_DBUS_ERROR, G_DBUS_ERROR_UNKNOWN_PROPERTY, "Unknown property %s", property_name);
    }
    return value;
}

const GDBusInterfaceVTable VTABLE = {item_method_call, item_get_property, nullptr, {}};

}  // namespace

TrayIcon::TrayIcon(std::string name, std::string title, std::vector<std::string> icon_paths,
                   std::vector<MenuItem> menu)
    : d(new Private)
{
    d->name = std::move(name);
    d->title = std::move(title);
    d->menu = std::move(menu);
    for (const auto &path: icon_paths) {
        if (auto pixmap = load_pixmap(path)) {
            d->pixmaps.push_back(std::move(*pixmap));
        } else {
            logger.warning("Cannot load tray icon {}", path);
        }
    }
}

TrayIcon::~TrayIcon()
{
    stop();
    delete d;
}

bool TrayIcon::run_detached()
{
    std::promise<bool> started;
    auto started_future = started.get_future();

    thread = std::thread([this, &started] {
        d->context = g_main_context_new();
        g_main_context_push_thread_default(d->context);
        d->loop = g_main_loop_new(d->context, FALSE);

        GError *error = nullptr;
        d->connection = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &error);
        if (!d->connection) {
            logger.warning("Tray icon is not supported on your platform (no D-Bus session bus: {})", error->message);
            g_error_free(error);
            started.set_value(false);
            g_main_context_pop_thread_default(d->context);
            return;
        }

        d->node_info = g_dbus_node_info_new_for_xml(INTROSPECTION_XML, nullptr);
        d->item_registration = g_dbus_connection_register_object(
            d->connection, ITEM_PATH, g_dbus_node_info_lookup_interface(d->node_info, "org.kde.StatusNotifierItem"),
            &VTABLE, d, nullptr, nullptr);
        d->menu_registration = g_dbus_connection_register_object(
            d->connection, MENU_PATH, g_dbus_node_info_lookup_interface(d->node_info, "com.canonical.dbusmenu"),
            &VTABLE, d, nullptr, nullptr);

        // Well-known name of the item, then registration with the watcher as soon as it is available
        d->bus_name = "org.kde.StatusNotifierItem-" + std::to_string(::getpid()) + "-1";
        d->own_id = g_bus_own_name_on_connection(d->connection, d->bus_name.c_str(), G_BUS_NAME_OWNER_FLAGS_NONE,
                                                 nullptr, nullptr, nullptr, nullptr);
        d->watch_id = g_bus_watch_name_on_connection(
            d->connection, WATCHER_NAME, G_BUS_NAME_WATCHER_FLAGS_NONE,
            [](GDBusConnection *, const gchar *, const gchar *, gpointer user_data) {
                auto *p = static_cast<Private *>(user_data);
                p->watcher_seen = true;
                p->register_with_watcher();
            },
            [](GDBusConnection *, const gchar *, gpointer user_data) {
                auto *p = static_cast<Private *>(user_data);
                if (p->watcher_seen) {
                    // The system tray stopped: the icon will be registered again when it comes back
                    logger.debug("System tray (StatusNotifierWatcher) disappeared");
                } else if (!p->watcher_warning_done) {
                    p->watcher_warning_done = true;
                    logger.warning("No system tray found (StatusNotifierWatcher): the tray icon is not displayed. "
                                   "On GNOME, enable the AppIndicator extension.");
                }
            },
            d, nullptr);

        started.set_value(true);
        g_main_loop_run(d->loop);

        g_bus_unwatch_name(d->watch_id);
        g_bus_unown_name(d->own_id);
        g_dbus_connection_unregister_object(d->connection, d->item_registration);
        g_dbus_connection_unregister_object(d->connection, d->menu_registration);
        g_dbus_connection_flush_sync(d->connection, nullptr, nullptr);
        g_dbus_node_info_unref(d->node_info);
        g_object_unref(d->connection);
        g_main_context_pop_thread_default(d->context);
    });

    const bool result = started_future.get();
    if (!result) {
        thread.join();
    }
    return result;
}

void TrayIcon::stop()
{
    if (thread.joinable()) {
        g_main_loop_quit(d->loop);
        if (thread.get_id() == std::this_thread::get_id()) {
            // Stopped from a menu action: the D-Bus thread ends by itself, its resources are kept
            thread.detach();
            return;
        }
        thread.join();
    }
    if (d->loop) {
        g_main_loop_unref(d->loop);
        d->loop = nullptr;
    }
    if (d->context) {
        g_main_context_unref(d->context);
        d->context = nullptr;
    }
}
