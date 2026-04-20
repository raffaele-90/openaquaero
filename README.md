*🇮🇹 [Leggi la documentazione in Italiano](README.it.md)*

# 💧 OpenAquaero 2.2

OpenAquaero is an open-source, native, and lightweight thermal control panel for Linux, specifically designed for the **Aquacomputer Aquaero 6 LT**. It provides a modern, focused interface for managing custom liquid cooling loops directly from your Linux desktop environment.

## ⚠ Scope and Current Limitations
This project focuses on delivering a streamlined, highly responsive control experience for the core components of your cooling loop. It is not intended to be a complete 1:1 replica of the official Windows software suite.
* **Hardware Support:** Currently manages the **4 main 12V outputs** (fans and pumps).
* **Real-Time Override:** The software operates in real-time. Writing thermal profiles permanently to the board's internal EPROM is not yet supported.
* **PWM/DC State:** Outputs currently rely on their last configured hardware state. Software switching between PWM and DC modes is under active development.
* **Extended Modules:** Aquabus devices and complex external alarm sensors are not currently managed.

## ✨ Key Features
OpenAquaero introduces several modern features tailored for Linux users:
- **Hardware Monitoring:** Reads CPU and GPU temperatures directly from the Linux kernel (`sysfs`), providing accurate low-overhead monitoring without requiring heavy background daemons. 
- **Smart OSD (On-Screen Display):** A borderless, scalable, and draggable floating overlay to monitor your loop's temperatures and RPMs seamlessly while gaming.
- **Process-Based Auto-Switch:** Dynamically links thermal profiles to specific applications. The software will automatically apply your designated cooling profile when a target process (e.g., a game or rendering software) is launched.
- **Adjustable Hysteresis Filter:** Utilizes a dynamic time-based moving average to smooth out sudden temperature spikes. This prevents abrupt fan speed changes and ensures gradual, quiet acoustic transitions.
- **Multilingual Interface:** Natively translated into English, Italian, German, French, and Spanish.

## 🛠 Installation (Arch Linux)
1. Clone this repository to your local machine.
2. Run `makepkg -si` to build the package, install it, and automatically apply the necessary `udev` rules.
3. *(Optional)* Install `python-pynvml` via pacman for extended hardware monitoring support.

## 📜 License
Released under the **GNU GPLv3**. This is an independent, community-driven project and is not affiliated with Aquacomputer.
