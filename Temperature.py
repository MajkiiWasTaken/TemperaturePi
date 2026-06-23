import os
import glob
import time
import asyncio

from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock

os.system("sudo modprobe w1-gpio")
os.system("sudo modprobe w1-therm")

MODBUS_MODULE_NAME = "Raspberry Pi 3B+ ver. 02"

time.sleep(2)

base_dir = "/sys/bus/w1/devices/"
devices = glob.glob(base_dir + "28*")

if len(devices) == 0:
    print("DS18B20 sensor was not found.")
    exit()

device_file = devices[0] + "/w1_slave"


def read_temp_raw():
    with open(device_file, "r") as f:
        return f.readlines()


def read_temp():
    lines = read_temp_raw()

    while lines[0].strip()[-3:] != "YES":
        time.sleep(0.2)
        lines = read_temp_raw()

    equals_pos = lines[1].find("t=")

    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

    return None

store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, [0] * 200)
)

context = ModbusServerContext(
    slaves=store,
    single=True
)

def string_to_registers(text, register_count):
    data = text.encode("ascii")

    max_bytes = register_count * 2

    if len(data) > max_bytes:
        data = data[:max_bytes]

    data = data + bytes(max_bytes - len(data))

    registers = []

    for i in range(0, max_bytes, 2):
        value = (data[i] << 8) | data[i + 1]
        registers.append(value)

    return registers

def write_module_name():
    registers = string_to_registers(MODBUS_MODULE_NAME, 32)

    context[0].setValues(3, 0, registers)

    print(f"Module name written to registers 0-31: {MODBUS_MODULE_NAME}")

async def update_temperature_register():
    while True:
        temp = read_temp()

        if temp is not None:
            value = int(temp * 100)

            context[0].setValues(3, 100, [value])

            print(f"Temperature: {temp:.2f} °C | Register 100: {value}")

        await asyncio.sleep(2)

async def main():
    write_module_name()

    asyncio.create_task(update_temperature_register())

    print("Modbus TCP server running on 0.0.0.0:5020")
    print(f"Register 0: module name ({MODBUS_MODULE_NAME})")
    print("Register 100: temperature * 100")

    await StartAsyncTcpServer(
        context=context,
        address=("0.0.0.0", 5020)
    )
 
asyncio.run(main())
