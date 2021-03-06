from . import application
from . import browser
from . import settings
from . import event
from PyQt4 import QtCore, QtGui

TOAST_WIDTH = 330
# Used for toast and chat window positioning
_margin = 10

sys_tray = None
show_hide = None

def init():
    base_url = "https://www.facebook.com"
    base_url_override = settings.get_setting("BaseUrl")
    if (base_url_override):
        print("BaseUrl:", base_url_override)
        base_url = base_url_override

    global main_window
    closable_main = not is_system_tray_enabled()
    main_window = browser.BrowserWindow(base_url + "/desktop/client/",
                                        closable=closable_main)
    main_window.set_size(212, 640)
    main_window.set_title("Messenger")
    def main_window_moved_or_resized():
        settings.set_setting(
            "MainWindowRectangle", main_window.get_rectangle())
    event.subscribe(main_window.MOVE_EVENT, main_window_moved_or_resized)
    event.subscribe(main_window.RESIZE_EVENT, main_window_moved_or_resized)
    event.subscribe(main_window.SHOW_EVENT, main_window_shown)
    event.subscribe(main_window.HIDE_EVENT, main_window_hidden)
    event.subscribe(main_window.CLOSE_EVENT, application.quit)
    def main_window_key_press(key):
        if key == QtCore.Qt.Key_Escape and is_system_tray_enabled():
            main_window.hide()
    event.subscribe(main_window.KEY_PRESS_EVENT, main_window_key_press)
    init_main_window()

    global chat_window
    chat_window = browser.BrowserWindow(base_url + "/desktop/client/chat.php",
                                        closable=False)
    chat_window.set_size(420, 340)
    def chat_window_moved_or_resized():
        settings.set_setting(
            "ChatWindowRectangle", chat_window.get_rectangle())
    event.subscribe(chat_window.MOVE_EVENT, chat_window_moved_or_resized)
    event.subscribe(chat_window.RESIZE_EVENT, chat_window_moved_or_resized)

    global toast_window
    toast_window = browser.BrowserWindow(
        base_url + "/desktop/client/toast.php")
    toast_window.style_toast()
    # height of one toast -- this will be overridden but just in case
    toast_window.set_size(TOAST_WIDTH, 72)
    event.subscribe(settings.AUTH_CHANGED_EVENT, toast_window.hide)

    # check if system tray should be enabled
    if is_system_tray_enabled():
        create_sys_tray()

def create_sys_tray():
    global sys_tray
    sysIcon = QtGui.QIcon(application.resource_path("fbmessenger.png"))
    sys_tray = QtGui.QSystemTrayIcon(sysIcon, application.get_qt_application())
    sys_tray.activated.connect(on_sys_tray_activated)

    sysTrayMenu = QtGui.QMenu()

    global show_hide
    show_hide = sysTrayMenu.addAction("")
    set_show_hide_text()
    show_hide.triggered.connect(show_or_hide_main_window)
    quit = sysTrayMenu.addAction("Quit")
    quit.triggered.connect(application.quit)
    sys_tray.setContextMenu(sysTrayMenu)
    sys_tray.setVisible(True)

def set_show_hide_text():
    if not show_hide:
        return
    show_hide.setText("Hide" if main_window.is_visible() else "Show")

def on_sys_tray_activated(reason):
    if (reason == QtGui.QSystemTrayIcon.Trigger or
            reason == QtGui.QSystemTrayIcon.DoubleClick):
        show_or_hide_main_window()

def show_or_hide_main_window():
    if main_window.is_visible():
        main_window.hide()
    else:
        main_window.show()

def main_window_shown():
    set_show_hide_text()
    settings.set_setting("Minimized", False)

def main_window_hidden():
    set_show_hide_text()
    settings.set_setting("Minimized", True)

# The main window's position is saved whenever it is moved or resized, so we
# restore it when the window is created.
def init_main_window():
    saved_rectangle = settings.get_setting("MainWindowRectangle")
    if saved_rectangle:
        main_window.set_rectangle(*saved_rectangle)
    main_window.fit_to_desktop()

    start_minimized = (settings.get_setting("Minimized", default=False) or
                       settings.get_setting("MinimizedOnStart", default=False))

    if not is_system_tray_enabled() or not start_minimized:
        main_window.show()

# The chat window is initially shown adjacent to the main window, bottom
# aligned on the left (or right if not enough space). If moved or resized, the
# position is remembered while the app is still running.
def show_chat_window():
    saved_rectangle = settings.get_setting("ChatWindowRectangle")
    if saved_rectangle:
        rect = saved_rectangle
    else:
        desk_x, desk_y, desk_width, desk_height = \
            main_window.get_desktop_rectangle()
        main_x, main_y, main_width, main_height = main_window.get_rectangle()
        chat_x, chat_y, chat_width, chat_height = chat_window.get_rectangle()
        default_x = main_x - chat_width - _margin
        if default_x < desk_x:
            default_x = main_x + main_width + _margin
        default_y = main_y + main_height - chat_height
        rect = (default_x, default_y, chat_width, chat_height)
    chat_window.set_rectangle(*rect)
    chat_window.fit_to_desktop()
    chat_window.show()

# The toast shows in the bottom right of the screen.
def _position_toast():
    x, y, width, height = toast_window.get_rectangle()
    dx, dy, dwidth, dheight = main_window.get_desktop_rectangle()
    newx = dx + dwidth - width - _margin
    newy = dy + dheight - height - _margin
    toast_window.set_position(newx, newy)

# Our JS has an interesting bug where it reports the wrong value to
# setToastHeight. For some reason the layout isn't finished for several more
# milliseconds, and the height grows. This hack has us actually reaching into
# the toast and pulling out the height of a single div, several times to make
# sure it stabilizes. God help us.
def _terrible_toast_height_hack():
    def inner_hack():
        height = toast_window.evaluate_js(
                'document.getElementById("toast-frame").offsetHeight')
        if height:
            toast_window.set_size(TOAST_WIDTH, height)
            _position_toast()
        else:
            print("Failed to hack out the toast height.")
    for delay_ms in (0, 10, 100, 1000):
        event.run_on_main_thread(inner_hack, delay_ms=delay_ms)

def show_toast():
    _position_toast()
    toast_window.show()
    _terrible_toast_height_hack()

def is_system_tray_enabled():
    if not QtGui.QSystemTrayIcon.isSystemTrayAvailable():
        return False
    return settings.get_setting("SystemTray", default=True)
