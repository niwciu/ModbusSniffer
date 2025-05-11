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


# 🛠️ Build & Install
## 1. General Requirements

### - Python 3 installed
### - pip3 installed 
#### Linux
```bash
sudo apt install python3-pip
```
#### Windows
```powershell
python -m ensurepip --upgrade
```

## 2. Clone the Repository

```bash
git clone https://github.com/niwciu/ModbusSniffer.git
cd ModbusSniffer
```
__________________________


## 3. Build Executable (for Ubuntu and Windows)
If you'd like to generate a standalone executable application for Ubuntu or Windows, you can follow the steps below.


> **Note:** f you only want to **run** the GUI app without generating a standalone executable, you can skip the build process and go straight to running the Python script as shown in
> 
> **▶️ Running GUI app without build**.

### Ubuntu (Linux) - Build with build.sh

## 3. Build Executable (for Ubuntu and Windows)
If you'd like to generate a standalone executable application for Ubuntu or Windows, you can follow the steps below.

> **Note:** If you only want to **run** the app and not build it, skip this step and go to **▶️ Running GUI app without build**.

> **Alternative Option:** If you don't want to build the application yourself, you can **download pre-built executables** for both Ubuntu and Windows from [this link](#) (insert actual download link here). 

### Ubuntu (Linux) - Build with build.sh

If you are using Ubuntu (or any other Linux-based OS), there's a script to automatically generate the application for you, and it will also add the application to your system's menu as a clickable entry.

1. Run the following command to build the executable:

    ```bash
    sudo chmod +x build.sh
    ./build.sh
    ```

    > **Note:**   
    This script will:
    >* Cleans up previous build files (build/, dist/, .spec, __pycache__).
    >* Create a virtual environment.
    >* Install the necessary dependencies.
    >* Use PyInstaller to build the application.
    >* Copy the resulting executable to the appropriate folder.
    >* Create a .desktop shortcut and add it to ~/.local/share/applications/, making the application available from your system's menu.

2. After running build.sh, you will find the built application in the dist/ folder. The .desktop file will also be placed in your system's application menu, allowing you to easily launch the application without needing to manually navigate to the executable.
### Windows - Build & Install

1. Run the following command to build the executable:

    ```powershell
    ./build.bat
    ```
    > **Note:**
    What build.bat does
    > * Cleans up previous build files (build/, dist/, .spec, __pycache__).
    > * Creates and activates a virtual environment (.venv/).
    > * Installs dependencies from requirements.txt and installs PyInstaller.
    > * Builds a standalone .exe from the Python script using PyInstaller and a custom icon.
    > * Creates desktop and Start Menu shortcuts pointing to the executable, using the icon.
    > * Deactivates the virtual environment and pauses for user review.


2. After running build.sh, you will find the built application in the dist/ folder. You will find also shortcuts on desktop as well as in the start menu on your system.

> **Alternative Option:** You can also **download pre-built executables** for Windows from [this link](#) (insert actual download link here). 


# ▶️ Running GUI app without build
## 1. General Requirements

### - Python 3 installed
### - pip3 installed 
```bash
sudo apt install python3-pip
```

## 2. Clone the Repository

```bash
git clone https://github.com/niwciu/ModbusSniffer.git
cd ModbusSniffer
```
## 3. Create and Activate Virtual Environment

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

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5.Run GUI app

```bash
python3 modbus_sniffer_GUI.py
```

## 6. Deactivate Virtual Environment
```bash
deactivate 
```

# 🎮 CLI app Usage

## 1. Clone the Repository

```bash
git clone https://github.com/niwciu/ModbusSniffer.git
cd ModbusSniffer
```

## 2. Detail information aout usage of CLI version


```bash
python3 modbus_sniffer.py -h
```
## 3. Example of usage - running sniffer on port USB0 with baudrate 115200 and no parity

```bash
python3 modbus_sniffer.py -p /dev/ttyUSB0 -b 115200 -r none
```


---

# 🆕 What’s New

For the full changelog, including detailed descriptions of all updates, please refer to the [CHANGELOG.md](CHANGELOG.md).

---

# 🔧 ToDo

- Integrate CSV logging with new modbus parser
- Improve GUI with:
    - Add frame filters

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

