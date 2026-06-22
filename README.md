# DS18B20 Modbus TCP Slave

![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-red) 
![Python](https://img.shields.io/badge/Python-3.13-blue) 
![Modbus](https://img.shields.io/badge/Protocol-Modbus%20TCP-green) 
![Sensor](https://img.shields.io/badge/Sensor-DS18B20-orange) 

This project reads temperature from a DS18B20 sensor connected to a Raspberry Pi and exposes it through Modbus TCP.

The Raspberry Pi acts as a Modbus TCP slave. A Modbus master can connect to it and read the current temperature.

<img width="540" height="304" alt="temp" src="https://github.com/user-attachments/assets/422354f5-c469-44cd-a01e-d63d390a007e" />

---

### Hardware

* Raspberry Pi
* DS18B20 temperature sensor
* 4.7 kΩ pull-up resistor

### Wiring

```
          4.7 kΩ
3.3V ─────/\/\/\────┐
                    │
                    ├──── DQ (DS18B20)
                    │
GPIO4 ──────────────┘

GND  ─────────────── GND (DS18B20)
3.3V ─────────────── VDD (DS18B20)

The DS18B20 data line (DQ) must be connected to GPIO4 and pulled up to 3.3 V using a 4.7 kΩ resistor.
```

---

### Installation

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install pymodbus==3.6.9
```

---

### Modbus Settings

* IP: Raspberry Pi IP
* Mode: Modbus TCP Slave
* Port: 5020
* Unit ID: 1
* Function Code: 03 (Read Holding Registers)
* Register: 100

The temperature is stored as:

```text
temperature × 100
```

Example:

```text
24.63 °C -> 2463
```

To get the temperature value:

```text
temperature = register_value / 100
```

### Author: Michal Švrček
