# Privacy Mode for Windows

A lightweight Windows utility that lets you quickly lock your workstation and request that the display turns off, while temporarily asking Windows to keep the system awake.

## Features

- **Global keyboard shortcut:** Press `Ctrl + Alt + L` to activate Privacy Mode.
- **Windows workstation lock:** Requests that Windows lock the current session.
- **Display power request:** Sends a monitor power-off request after a short delay.
- **Temporary sleep prevention:** Requests that Windows keep the system awake while Privacy Mode is active.
- **Automatic restoration:** When the session is unlocked, the utility clears its execution-state request.
- **Logging:** Records application and Windows API events in `privacy_mode_log.txt`.
- **No permanent power-plan changes:** Does not modify the user's Windows power-plan settings.

## Requirements

- Windows 10 or Windows 11.
- Python 3.10 or later.
- No third-party Python packages are required.

## Run

1. Download or clone this repository.
2. Open a terminal in the project folder.
3. Run:

   ```powershell
   python privacy_mode.py
   ```

4. Keep the program running.
5. Press **Ctrl + Alt + L** whenever you want to activate Privacy Mode.
6. Unlock your Windows session normally to end Privacy Mode and restore the utility's normal power-state request.

## How it works

The utility uses Python's built-in `ctypes` module to call Windows APIs. When the shortcut is pressed, it requests that Windows:

1. Keep the system awake temporarily.
2. Lock the current workstation session.
3. Send a monitor power-off command after approximately one second.

When Windows reports that the session has been unlocked, the utility clears the execution-state request it previously made.

## Notes and limitations

- The application must be running for the global shortcut to work.
- The monitor power-off request is handled by Windows and the display hardware. Actual behavior can vary by monitor, graphics driver, and system configuration.
- The sleep-prevention request is temporary and does not guarantee that every application, network connection, or background transfer will continue under every power state or system condition.
- This utility does not change permanent Windows sleep, display, or power-plan settings.
- The log file is created beside the script when the program runs. It is excluded from version control.

## License

No license has been specified for this repository yet. All rights are reserved by default unless the repository owner adds a license.
