
# 🐍 ModbusSniffer – Free Modbus RTU Analyzer with GUI (Python / PyQt6)

A lightweight and user-friendly Modbus RTU sniffer tool with a graphical interface.  
Easily analyze and debug communication between PLCs, HMIs, and other Modbus RTU devices via serial ports.

[![GitHub release](https://img.shields.io/github/v/release/niwciu/ModbusSniffer)](https://github.com/niwciu/ModbusSniffer/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<div align="center">
<img src="https://niwciu.github.io/ModbusSniffer/gui.gif" alt="Demo" />
</div>

---

## 🔧 Features

- 🧰 Sniffs raw Modbus RTU frames from serial ports (RS-485, USB)
- 🖥️ GUI interface built with PyQt6
- 📋 Frame table: Real-time decoded Modbus traffic
- 🌈 Color-coded logging of request–response frames
- 🪟 Cross-platform: Windows & Linux
- 🆓 MIT licensed, open-source

---

## 📦 Installation

Install directly from PyPI:

```bash
pip install modbus-sniffer
```
or download Binary files for Ubuntu and Windows from [here](https://github.com/niwciu/ModbusSniffer/releases).

You can also build and install app from sourcess. [Click here](CONTRIBUTING.md#%EF%B8%8F-build--install) for deatails about it.


---

## ▶️ Usage

### 🎛️ Run GUI:

```bash
modbus-sniffer-gui
```

### 🖥️ Run CLI:
To list all options:
```bash
modbus-sniffer -h
```


Example of runnig sniffer on ttyUSB0 with baud 115200 and no parity:
```bash
modbus-sniffer -p /dev/ttyUSB0 -b 115200 -r none
```

For more usage options, development guide, and installation from source, visit the GitHub repository:

👉 [ModbusSniffer on GitHub](https://github.com/niwciu/ModbusSniffer)

---
## 🤝 Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

---

## 📜 License

MIT License — see the [LICENSE](LICENSE) file for details.  
This project is a fork of [BADAndrea ModbusSniffer](https://github.com/BADAndrea/ModbusSniffer), maintained by **niwciu** with enhancements described above.


<div align="center">

---
<img src="https://github.com/user-attachments/assets/f4825882-e285-4e02-a75c-68fc86ff5716" alt="myEmbeddedWayBanerWhiteSmaller"/>

---
</div>