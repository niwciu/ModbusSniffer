# 🚀 ModbusSniffer with GUI 🚀

Welcome to **ModbusSniffer** — an enhanced fork of the original ModbusSniffer tool for RTU traffic analysis. 


Print all packets on bus from either slave or master and writes them to a logfile.

Useful for sniffing packets between two devices to ensure correct operation.

This fork bring lot of improvements from backend as welll as new GUI with some features.

<div align="center">


![Demo](https://github.com/niwciu/ModbusSniffer/blob/main/doc/gui.gif?raw=true)

</div>



---


# ❓ Why This Fork?

This version brings:

* **💻 Code Refactor:** Modular architecture with clear separation into modules and classes
* **🛠️ Parser Overhaul:** Fully rewritten `ModbusParser` as a dedicated class
* **🖥️ GUI Added:** A basic graphical interface for easier use
* **🔄 CLI → GUI:** All command-line functionality integrated into the GUI
* **📋 Frame Table:** Real-time view of the latest captured frames
* **🌈 Live Logging:** Color-coded request–response pairs; unmatched requests highlighted in red

---


# 🛠️ Installation & Setup
## 1. General Requirements

### - Python 3 installed
### - pip3 installed 
```bash
sudo apt install python3-pip
```

## 1. Clone the Repository

```bash
git clone https://github.com/niwciu/ModbusSniffer.git
cd ModbusSniffer
```

## 2. Create and Activate Virtual Environment

### Linux / macOS

```bash
python3 -m venv .venv         # create venv
source .venv/bin/activate     # activate             
```

### Windows (PowerShell)

```powershell
python -m venv .venv               # create venv
.\.venv\Scripts\Activate.ps1       # activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```
## 4. Deactivate Virtual Environment
```bash
deactivate 
```

# 🎮 Usage
## Create and Activate Virtual Environment befor running app
(Info can be found in section  **🛠️ Installation & Setup** above)
## CLI Mode
### Detail information aout usage of CLI version

```bash
python3 modbus_sniffer.py -h
```
### Example of usage

```bash
python3 modbus_sniffer.py -p /dev/ttyUSB0 -b 115200 -r none
```

## GUI Mode

```bash
python modbus_sniffer_GUI.py
```

---

# 🆕 What’s New (Changelog)

1. 📦 **Modularization:** Splitted code into modules and classes for maintainability
2. 🧩 **Parser Rework:** `ModbusParser` class completely rewritten for clarity and extensibility
3. 🖼️ **GUI Interface:** Added a simple, user-friendly GUI
4. 🔁 **Full CLI Feature Set in GUI:** All previous CLI commands available via graphical menus (CSV under dev)
5. 📊 **Frame Table View:** Displays the last captured frames with filtering options
6. 🌈 **Enhanced Live Logging:** Color distinction for request/response pairs; unmatched requests marked in red

---
# 🔧 ToDo

- Test of new parser with all integrated functions - pending
- Integrate CSV logging with new modbus parser
- Improve GUI with:
    - Clear button for logs and table view
    - Add frame filters
    - Add comoboxe for selecting pors from ports availabel in the system
    - Add comoboxe for selecting predefined baudrate

# 📚 Documentation & Support

* Detailed documentation will be available in the `docs/` folder soon.
* Questions or issues? Open an issue in GitHub or contact the maintainers.

---

# 🤝 Contributing

Contributions are welcome! Please fork the repo and submit a pull request:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature-name`)
3. Commit your changes (`git commit -m "Add feature"`)
4. Push to branch (`git push origin feature-name`)
5. Open a Pull Request

---

# 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

This project is a fork of [BADAndrea ModbusSniffer](https://github.com/BADAndrea/ModbusSniffer)

Fork maintained by **niwciu** with enhancements described above.

---

❤️ Thank you for using this version of ModbusSniffer!

</br></br>
<div align="center">

***

![myEmbeddedWayBanerWhiteSmaller](https://github.com/user-attachments/assets/f4825882-e285-4e02-a75c-68fc86ff5716)
***
</div>