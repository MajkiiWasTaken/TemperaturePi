import os
import glob
import time
import asyncio

from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock

os.system("sudo modprobe w1-gpio")
os.system("sudo modprobe w1-therm")

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
    hr=ModbusSequentialDataBlock(1, [0] * 200)
)

context = ModbusServerContext(
    slaves=store,
    single=True
)

async def update_temperature_register():
    while True:
        temp = read_temp()

        if temp is not None:
            value = int(temp * 100)

            context[0].setValues(3, 100, [value])

            print(f"Temperature: {temp:.2f} °C | Register 100: {value}")

        await asyncio.sleep(2)

async def main():
    asyncio.create_task(update_temperature_register())

    print("Modbus TCP server running on 0.0.0.0:5020")
    print("Read Holding Register 0, value / 100 = temperature °C")

    await StartAsyncTcpServer(
        context=context,
        address=("0.0.0.0", 5020)
    )


asyncio.run(main())
