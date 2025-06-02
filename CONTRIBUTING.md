
# 🐍 ModbusSniffer – Free Modbus RTU Analyzer with GUI (Python / PyQt6)

A lightweight and user-friendly Modbus RTU sniffer tool with a graphical interface.  
Easily analyze and debug communication between PLCs, HMIs, and other Modbus RTU devices via serial ports.

[![GitHub release](https://img.shields.io/github/v/release/niwciu/ModbusSniffer)](https://github.com/niwciu/ModbusSniffer/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<div align="center">
<img src="https://github.com/niwciu/ModbusSniffer/blob/main/doc/gui.gif?raw=true" alt="Demo" />
</div>

---

## 🚀 Why ModbusSniffer (This Fork)?

### 🔍 General Highlights

- 🧰 Sniffs raw Modbus RTU frames from serial ports (RS-485, USB)
- 🖥️ Graphical User Interface (PyQt6) — no terminal needed
- 📋 Frame table: Real-time view with decoded address, function code, and data
- 🌈 Live Logging: Color-coded request–response pairs, unmatched requests highlighted
- 🪟 Cross-platform: Windows & Linux
- 🆓 Free & Open Source (MIT license)

### 🛠️ Why This Fork (What's New)

- 💻 Modular code refactor — clear separation into modules and classes
- 🧠 Rewritten Modbus parser (`ModbusParser` class) with clean structure
- 🖥️ Fully integrated GUI (previously only CLI)
- 🔄 All command-line functionality preserved and upgraded into the GUI

---

## 🧰 Easy Installation (Pre-built Binaries or Install Scripts for Windows and Linux)

You don't need to build anything manually!  
This project uses GitHub Actions (GHA) to automatically build and publish verified binaries for each release.  
Pre-built versions for Windows and Ubuntu are available under the [Releases](https://github.com/niwciu/ModbusSniffer/releases) tab.

For custom builds and automatic shortcut setup, see the **🛠️ Build & Install** section below.

---

## 🛠️ Build & Install

### 1. General Requirements

#### - Python 3 installed
#### - pip3 installed 

#### 🐧 Linux
```bash
sudo apt install python3-pip
```

#### 🪟 Windows
```powershell
python -m ensurepip --upgrade
```

### 2. Clone the Repository

```bash
git clone https://github.com/niwciu/ModbusSniffer.git
cd ModbusSniffer/install_scripts
```

### 3. Build Executable (for Ubuntu and Windows)

> **Note:** If you only want to **run** the app and not build it, skip this step and go to **▶️ Running GUI app without build**.

#### 🐧 Linux

```bash
sudo chmod +x build.sh
./build.sh
```

> This script:
> * Cleans previous build files (build/, dist/, .spec, \_\_pycache\_\_)
> * Creates a virtual environment and installs dependencies
> * Uses PyInstaller to build the app
> * Adds Start Menu and desktop shortcuts

#### 🪟 Windows

```powershell
./build.bat
```

> This script:
> * Cleans previous build files
> * Sets up a virtual environment and installs dependencies
> * Builds a standalone `.exe` using PyInstaller
> * Adds desktop and Start Menu shortcuts

---

## ▶️ Running GUI App (installed via pip)
### 1. Clone repository

```bash
git clone https://github.com/niwciu/ModbusSniffer.git
cd ModbusSniffer
```

### 2. Create and Activate Virtual Environment
#### 🐧 Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 🪟 Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install package and development tools

```bash
pip install -e .[dev]
```

### 4. Run GUI app 🎛️ 🧩
```bash
modbus-sniffer-gui
```
> Note: virtual environment (.venv) must be active

### 5. Deactivate Virtual Environment
```bash
deactivate
```

---

## 🎮 Running the CLI App (installed via pip)
### 1. Clone repository
```bash
git clone https://github.com/niwciu/ModbusSniffer.git
cd ModbusSniffer
```
### 2. Create and Activate Virtual Environment

#### 🐧 Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 🪟 Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install package and development tools

```bash
pip install -e .[dev]
```

### 4. Run CLI Help 🖥️ 

```bash
modbus-sniffer -h
```
> Note: virtual environment (.venv) must be active.

### 5. Example of usage 🧪
Run modbus-sniffer CLI app on port USB0 with baud 115200 and parity=none
```bash
modbus-sniffer -p /dev/ttyUSB0 -b 115200 -r none
```
> Note: virtual environment (.venv) must be active.

### 6. Deactivate Virtual Environment

```bash
deactivate
```

## ▶️ Running GUI App without installation
### 1. Clone repository

```bash
git clone https://github.com/niwciu/ModbusSniffer.git
cd ModbusSniffer
```

### 2. Create and Activate Virtual Environment
#### 🐧 Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 🪟 Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install requirements

```bash
pip install -r ./install_scripts/requirements.txt
```

### 4. Run GUI app 🎛️ 🧩
```bash
cd src/modbus_sniffer
python gui.py
```
> Note: virtual environment (.venv) must be active

### 5. Deactivate Virtual Environment
```bash
deactivate
```

---

## 🎮 Running the CLI App without installation
### 1. Clone repository
```bash
git clone https://github.com/niwciu/ModbusSniffer.git
cd ModbusSniffer
```
### 2. Create and Activate Virtual Environment

#### 🐧 Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 🪟 Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install requirements

```bash
pip install -r ./install_scripts/requirements.txt
```

### 4. Run CLI Help 🖥️ 

```bash
cd src/modbus_sniffer
python cli.py -h
```
> Note: virtual environment (.venv) must be active.

### 5. Example of usage 🧪
Run modbus-sniffer CLI app on port USB0 with baud 115200 and parity=none
```bash
cd src/modbus_sniffer #optional - if running from project main folder
python cli.py -p /dev/ttyUSB0 -b 115200 -r none
```
> Note: virtual environment (.venv) must be active.

### 6. Deactivate Virtual Environment

```bash
deactivate
```

---

## 🆕 What’s New

See the full [CHANGELOG.md](CHANGELOG.md) for details.

---

## 🔧 ToDo
- Improve GUI with:
  - Add frame filtering
- Add posibility to set log files path 


## 📚 Documentation & Support

- Detailed documentation will be available in the `docs/` folder soon.
- Questions or issues? Open an [issue](https://github.com/niwciu/ModbusSniffer/issues) or join the [Discussions](https://github.com/niwciu/ModbusSniffer/discussions).

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository  
2. Create your feature branch (`git checkout -b feature-name`)  
3. Commit your changes (`git commit -m "Add feature"`)  
4. Push to branch (`git push origin feature-name`)  
5. Open a Pull Request  

After cloning the repository and setting up a virtual environment, you can install all development tools (used in CI/CD pipeline and for local testing, linting, and packaging) with:

```bash
pip install -e .[dev]
```
This includes formatters, linters, type checkers, test runners, and build tools.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file.

This project is a fork of [BADAndrea ModbusSniffer](https://github.com/BADAndrea/ModbusSniffer)  
Fork maintained by **niwciu** with enhancements described above.

---

❤️ Thank you for using this version of ModbusSniffer!

<div align="center">

---
<img src="https://github.com/user-attachments/assets/f4825882-e285-4e02-a75c-68fc86ff5716" alt="myEmbeddedWayBanerWhiteSmaller"/>

---
</div>