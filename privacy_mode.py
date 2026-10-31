import ctypes
from ctypes import wintypes
import time
import sys



from datetime import datetime
import os

LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "privacy_mode_log.txt"
)

def log_event(message):
    timestamp = datetime.now().astimezone().strftime(
        "%Y-%m-%d %H:%M:%S.%f %z"
    )
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as exc:
        print(f"[LOG ERROR] Could not write log file: {exc}", flush=True)


# ============================================================
# Windows API
# ============================================================

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
wtsapi32 = ctypes.WinDLL("wtsapi32", use_last_error=True)

LRESULT = ctypes.c_ssize_t

# ============================================================
# Constants
# ============================================================

WM_HOTKEY = 0x0312
WM_WTSSESSION_CHANGE = 0x02B1
WM_TIMER = 0x0113
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002

WTS_SESSION_UNLOCK = 0x8
NOTIFY_FOR_THIS_SESSION = 0

WM_SYSCOMMAND = 0x0112
SC_MONITORPOWER = 0xF170
HWND_BROADCAST = 0xFFFF

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
HOTKEY_ID = 1
TIMER_ID = 1

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

# ============================================================
# Windows structures
# ============================================================

WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


# ============================================================
# Function declarations
# ============================================================

user32.RegisterHotKey.argtypes = [
    wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT
]
user32.RegisterHotKey.restype = wintypes.BOOL

user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL

user32.LockWorkStation.argtypes = []
user32.LockWorkStation.restype = wintypes.BOOL

user32.SendMessageW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.SendMessageW.restype = LRESULT

user32.DefWindowProcW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.DefWindowProcW.restype = LRESULT

user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL

user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None

user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
    wintypes.DWORD, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.HWND,
    wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.GetMessageW.argtypes = [
    ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT
]
user32.GetMessageW.restype = ctypes.c_int

user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.restype = LRESULT

user32.SetTimer.argtypes = [
    wintypes.HWND, ctypes.c_size_t, wintypes.UINT, wintypes.LPVOID
]
user32.SetTimer.restype = ctypes.c_size_t

user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
user32.KillTimer.restype = wintypes.BOOL

# IMPORTANT: GetModuleHandleW belongs to kernel32, not user32.
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
kernel32.SetThreadExecutionState.restype = wintypes.DWORD

wtsapi32.WTSRegisterSessionNotification.argtypes = [
    wintypes.HWND, wintypes.DWORD
]
wtsapi32.WTSRegisterSessionNotification.restype = wintypes.BOOL

wtsapi32.WTSUnRegisterSessionNotification.argtypes = [wintypes.HWND]
wtsapi32.WTSUnRegisterSessionNotification.restype = wintypes.BOOL

# ============================================================
# Privacy Mode
# ============================================================

privacy_mode_active = False
window_handle = None


def prevent_sleep():
    log_event("POWER: calling SetThreadExecutionState to prevent system sleep")
    result = kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    )
    log_event(f"POWER: SetThreadExecutionState returned {result}")
    if result == 0:
        log_event("POWER ERROR: could not request sleep prevention")
        return False
    log_event("POWER: sleep-prevention request accepted")
    return True


def restore_normal_sleep():
    log_event("POWER: calling SetThreadExecutionState to restore normal behavior")
    result = kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    log_event(f"POWER: restore call returned {result}")
    if result == 0:
        log_event("POWER ERROR: could not restore normal power behavior")
        return False
    log_event("POWER: normal behavior restore request accepted")
    return True


def activate_privacy_mode():
    global privacy_mode_active

    if privacy_mode_active:
        log_event("HOTKEY: pressed while Privacy Mode already active")
        return

    log_event("HOTKEY: activation handler started")

    if not prevent_sleep():
        return

    log_event("LOCK: calling LockWorkStation")
    lock_result = user32.LockWorkStation()
    log_event(f"LOCK: LockWorkStation returned {lock_result}")
    if not lock_result:
        log_event("LOCK ERROR: Windows lock request failed")
        restore_normal_sleep()
        return

    privacy_mode_active = True
    log_event("STATE: privacy_mode_active set to True")

    timer_result = user32.SetTimer(window_handle, TIMER_ID, 1000, None)
    log_event(f"TIMER: SetTimer returned {timer_result}")
    if not timer_result:
        log_event("TIMER WARNING: timer creation failed; display-off skipped")
        log_event("STATE: sleep-prevention request remains active until unlock")


def deactivate_privacy_mode():
    global privacy_mode_active

    log_event(f"UNLOCK HANDLER: called while privacy_mode_active={privacy_mode_active}")
    if not privacy_mode_active:
        log_event("UNLOCK HANDLER: no active privacy mode; no power change made")
        return

    log_event("UNLOCK HANDLER: restoring power behavior")
    restore_normal_sleep()
    privacy_mode_active = False
    log_event("STATE: privacy_mode_active set to False; privacy mode ended")


@WNDPROC
def window_proc(hwnd, msg, wparam, lparam):
    global privacy_mode_active

    if msg == WM_HOTKEY and wparam == HOTKEY_ID:
        log_event(f"WINDOW MESSAGE: WM_HOTKEY received, id={wparam}")
        activate_privacy_mode()
        return 0

    if msg == WM_TIMER and wparam == TIMER_ID:
        log_event(f"WINDOW MESSAGE: WM_TIMER received, id={wparam}")
        user32.KillTimer(hwnd, TIMER_ID)
        log_event("DISPLAY: sending monitor power-off request")
        send_result = user32.SendMessageW(
            HWND_BROADCAST,
            WM_SYSCOMMAND,
            SC_MONITORPOWER,
            2
        )
        log_event(f"DISPLAY: SendMessageW returned {send_result}")
        log_event("DISPLAY: display-off request sent")
        return 0

    if msg == WM_WTSSESSION_CHANGE:
        log_event(
            f"SESSION EVENT: WM_WTSSESSION_CHANGE received; "
            f"wParam={wparam}, lParam={lparam}, "
            f"privacy_mode_active={privacy_mode_active}"
        )
        if wparam == WTS_SESSION_UNLOCK:
            log_event("SESSION EVENT: WTS_SESSION_UNLOCK received")
            user32.KillTimer(hwnd, TIMER_ID)
            deactivate_privacy_mode()
        elif wparam == 0x7:
            log_event("SESSION EVENT: WTS_SESSION_LOCK received")
        else:
            log_event(f"SESSION EVENT: other session change code={wparam}")
        return 0

    if msg == WM_CLOSE:
        user32.DestroyWindow(hwnd)
        return 0

    if msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0

    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def main():
    global window_handle

    log_event("PROGRAM: starting Privacy Mode")
    print("========================================")
    print("        PRIVACY MODE FOR WINDOWS")
    print("========================================")
    print("Hotkey: CTRL + ALT + L")
    print("Normal Windows power settings are not changed.")
    print(f"Log file: {LOG_FILE}")
    print()

    hinstance = kernel32.GetModuleHandleW(None)
    if not hinstance:
        raise ctypes.WinError(ctypes.get_last_error())

    class_name = "PrivacyModeWindow"

    wnd_class = WNDCLASSW()
    wnd_class.style = 0
    wnd_class.lpfnWndProc = window_proc
    wnd_class.cbClsExtra = 0
    wnd_class.cbWndExtra = 0
    wnd_class.hInstance = hinstance
    wnd_class.hIcon = None
    wnd_class.hCursor = None
    wnd_class.hbrBackground = None
    wnd_class.lpszMenuName = None
    wnd_class.lpszClassName = class_name

    if not user32.RegisterClassW(ctypes.byref(wnd_class)):
        raise ctypes.WinError(ctypes.get_last_error())

    window_handle = user32.CreateWindowExW(
        0, class_name, "Privacy Mode", 0,
        0, 0, 0, 0, None, None, hinstance, None
    )
    if not window_handle:
        raise ctypes.WinError(ctypes.get_last_error())

    if not user32.RegisterHotKey(
        window_handle, HOTKEY_ID,
        MOD_CONTROL | MOD_ALT, ord("L")
    ):
        raise ctypes.WinError(ctypes.get_last_error())

    if not wtsapi32.WTSRegisterSessionNotification(
        window_handle, NOTIFY_FOR_THIS_SESSION
    ):
        user32.UnregisterHotKey(window_handle, HOTKEY_ID)
        raise ctypes.WinError(ctypes.get_last_error())

    log_event("PROGRAM: ready; hotkey CTRL+ALT+L registered")
    print("[INFO] Keep this program running while using the hotkey.")
    print()

    msg = MSG()

    try:
        while True:
            result = user32.GetMessageW(
                ctypes.byref(msg), None, 0, 0
            )

            if result == -1:
                raise ctypes.WinError(ctypes.get_last_error())
            if result == 0:
                break

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    except KeyboardInterrupt:
        log_event("PROGRAM: KeyboardInterrupt received; stopping")

    finally:
        log_event(f"PROGRAM: cleanup started; privacy_mode_active={privacy_mode_active}")
        if privacy_mode_active:
            log_event("PROGRAM: active mode found during shutdown; restoring power behavior")
            restore_normal_sleep()

        wtsapi32.WTSUnRegisterSessionNotification(window_handle)
        user32.UnregisterHotKey(window_handle, HOTKEY_ID)

        if window_handle:
            user32.DestroyWindow(window_handle)

        log_event("PROGRAM: stopped")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log_event(f"FATAL ERROR: {type(exc).__name__}: {exc}")
        input("Press Enter to close...")
