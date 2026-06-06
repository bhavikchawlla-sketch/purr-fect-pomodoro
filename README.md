# Comnyang 🐱

A native, interactive desktop pet cat for Linux/Ubuntu that lives on your screen, reacts to your keyboard and mouse activity, and keeps you productive with built-in productivity widgets.

Inspired by "Comnyang", this application is built using **Python 3**, **PyQt6** (for the transparent GUI overlay), **pynput** (for input reactivity), **psutil** (for background process monitoring), and **Pillow** (for programmatic sprite tinting).

---

## Features

* 🐱 **Desktop Overlay**: Frameless, transparent window that sits on top of all other windows.
* 🖱️ **Click & Drag**: Position the cat anywhere on your screens.
* ⚡ **Input Reactivity**:
  * Loops `idle` animation (wagging tail, blinking eyes) when you are inactive.
  * Transitions to `typing` (mashing a tiny keyboard) when you type.
  * Transitions to `tracking` (raising its paw) when you move or scroll the mouse.
* 🎨 **Color Themes**: Right-click to tint the cat programmatically with presets: *Orange Tabby (Default)*, *Black*, *White*, *Grey*, *Calico*, or *Siamese*.
* 🍅 **Pomodoro Timer**: A built-in 25m work / 5m break timer displaying countdowns in a clean overlay.
* 🧘 **Stretch Reminders**: Sends a native desktop notification (`notify-send`) and runs a stretching animation every 45 minutes to remind you to move.
* 🧠 **AI/Dev Tool Focus Mode**: Scans background processes. If developer or AI tools (like VS Code, Cursor, Claude, etc.) are running, the cat puts on tiny glasses and gets into a `focused` posture.

---

## Installation & Setup

### Prerequisites (Ubuntu/Debian)

To run Comnyang, you need to install Python and its GUI/system bindings. The cleanest way to install them without running into python environment restrictions (PEP 668) is via your system package manager:

```bash
sudo apt update
sudo apt install -y python3-pyqt6 python3-pynput python3-psutil python3-pil python3-evdev python3-xlib
```

### Running the App

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/comnyang.git
   cd comnyang
   ```
2. Launch the application:
   ```bash
   python3 main.py
   ```

*(On first launch, Comnyang will automatically generate its pixel-art sprites folder, so no additional assets download is necessary!)*

---

## Project Structure

```
comnyang/
├── main.py                  # App entry point & event loop wiring
├── requirements.txt         # Package requirements
├── core/
│   ├── window.py            # Transparent draggable Qt window & right-click menu
│   ├── animation.py         # Sprite frame QTimer loop & priorities
│   ├── sprite_generator.py  # Programmatic pixel-art generator
│   └── color_filter.py      # Real-time LUT-based image tinting
├── input_tracking/
│   └── tracker.py           # Daemon input listener (pynput)
├── productivity/
│   ├── pomodoro.py          # Pomodoro state machine
│   └── stretch_reminder.py  # Periodic stretch notifier
└── monitoring/
    └── process_monitor.py   # Background process scanner (psutil)
```

---

## License

This project is licensed under the LGPL License.
