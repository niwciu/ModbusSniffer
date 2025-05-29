
# ModbusSniffer




<table style="width: 100%; border: none; align:center">
<tr>
  </td>
    <td style="width: 160px; vertical-align: top;">
    <img src="./img/icon-4.png" alt="ModbusSniffer logo">
  </td>
  <td style="vertical-align: top;">
    <strong>ModbusSniffer</strong> is a lightweight, cross-platform desktop application for monitoring Modbus RTU communication via serial ports.<br><br>
    Designed for engineers, technicians, and automation developers, it simplifies troubleshooting by showing decoded Modbus traffic in real-time.

</tr>
</table>
<div align="center">
<img src="https://github.com/niwciu/ModbusSniffer/blob/main/doc/gui.gif?raw=true" alt="Demo" />
</div>

---

## 🚀 Key Features

- ✅ Real-time Modbus RTU frame capturing
- ✅ Live Frame table view
- ✅ Friendly graphical interface (PyQt6)
- ✅ Message decoding with function and address information
- ✅ Filtering, sorting and searching captured data
- ✅ Exporting logs to txt and CSV
- ✅ Sniffs raw Modbus RTU frames from serial ports (RS-485, USB)
- ✅ Color-coded logging of request–response frames in terminal view
- ✅ Cross-platform: Windows & Linux
- ✅ MIT licensed, open-source

---

## 📦 Download & Installation

Install directly from PyPI:

```bash
pip install modbus-sniffer
```
or download Binary files for Ubuntu and Windows from [here](https://github.com/niwciu/ModbusSniffer/releases).

You can also build and install app from sourcess. [Click here](https://github.com/niwciu/ModbusSniffer/blob/main/CONTRIBUTING.md#%EF%B8%8F-build--install)
 for deatails about it.



---

## 🖥️ User Interface Overview

- **Top Toolbar**: Connect, Start/Stop Sniffing, Export Logs
- **Main Table View**: Real-time display of Modbus requests and responses
- **Filters Panel**: Filter by device ID, function code, or address

---

## 📚 How It Works

ModbusSniffer opens a serial port and listens for Modbus RTU traffic. It parses each Modbus frame and displays it in a structured table.

> ℹ️ Tip: Use a USB Modbus sniffer cable or RS485 tap to capture traffic without interfering with the bus.

---

## ❓ FAQ

**Q: Can I use it with USB-to-RS485 converters?**  
Yes! As long as the converter exposes a COM port, it works out of the box.

**Q: Is it safe to use on a live bus?**  
Yes — it is passive. It does not transmit any data.

**Q: Can I decode custom Modbus function codes?**  
Not yet — support for custom decoding is planned in a future release.

---

## 📬 Support & Feedback

If you find a bug or have suggestions, [open an issue on GitHub](https://github.com/niwciu/ModbusSniffer/issues).

MIT Licensed. Created by [niwciu](https://github.com/niwciu).




## ▶️ Usage

### 🎛️ Run GUI from bash:

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

Please see [CONTRIBUTING.md](https://github.com/niwciu/ModbusSniffer/blob/main/CONTRIBUTING.md)
 for development setup and contribution guidelines.

---

## 📜 License

MIT License — see the [LICENSE](https://github.com/niwciu/ModbusSniffer/blob/main/LICENSE) file for details.  
This project is a fork of [BADAndrea ModbusSniffer](https://github.com/BADAndrea/ModbusSniffer), maintained by **niwciu** with enhancements described above.

---

<img src="https://github.com/user-attachments/assets/f4825882-e285-4e02-a75c-68fc86ff5716" alt="myEmbeddedWayBanerWhiteSmaller"/>

***
</div>