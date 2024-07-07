ModbusSniffer
=============

Modbus RTU packet sniffer

Print all packets on bus from either slave or master and writes them to a logfile.
Useful for sniffing packets between two devices to ensure correct operation.

Documentation
-------------

```text
Usage:  
  python modbus_sniffer.py [arguments]

Arguments:  
  -p, --port        select the serial port (Required)  
  -b, --baudrate    set the communication baud rate, default = 9600 (Option)  
  -r, --parity      select parity, default = even (Option)"
  -t, --timeout     overrite the calculated inter frame timeout, default = 0.0034375s (Option)
  -l, --log-to-file console log is written to file, default = EVEN (Option)
  -h, --help        print the documentation
```

Project Informations
--------------------

### - License

[![GitHub](https://img.shields.io/github/license/ekristoffe/ModbusSniffer)](https://github.com/ekristoffe/ModbusSniffer/blob/main/LICENSE)

Disclaimer
----------

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
