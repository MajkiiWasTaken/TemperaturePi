import os
import glob
import time
import asyncio

from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock

os.system("sudo modprobe w1-gpio")
os.system("sudo modprobe w1-therm")

MODBUS_MODULE_NAME = "Raspberry Pi 3B+ ver. 02"

BASE_DIR = "/sys/bus/w1/devices/"
TEMP_REGISTER = 100
STATUS_REGISTER = 101
TEMP_UPDATE_INTERVAL_SEC = 2

# Register 100 (mbpoll 101): temperature * 100
# Register 101 (mbpoll 102): sensor status
#   1 = sensor connected / OK
#   0 = sensor disconnected / read error

# Give kernel modules a moment to initialize.
time.sleep(2)


store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, [0] * 200)
)

context = ModbusServerContext(
    slaves=store,
    single=True
)


def find_sensor_file():
    """Find an available DS18B20 sensor dynamically."""
    devices = glob.glob(BASE_DIR + "28*")

    if not devices:
        return None

    return devices[0] + "/w1_slave"


def read_temp_raw():
    """Read raw DS18B20 data. Returns None if the sensor is unavailable."""
    device_file = find_sensor_file()

    if device_file is None:
        return None

    try:
        with open(device_file, "r") as f:
            lines = f.readlines()
    except (FileNotFoundError, OSError):
        return None

    if len(lines) < 2:
        return None

    return lines

def read_temp():
    """Read temperature in Celsius. Returns None if the sensor cannot be read."""
    # DS18B20 can occasionally report a failed CRC. Retry a few times,
    # but never block forever.
    for _ in range(5):
        lines = read_temp_raw()

        if lines is None:
            return None

        if lines[0].strip().endswith("YES"):
            equals_pos = lines[1].find("t=")

            if equals_pos == -1:
                return None

            try:
                temp_string = lines[1][equals_pos + 2:].strip()
                return float(temp_string) / 1000.0
            except ValueError:
                return None

        time.sleep(0.2)

    return None


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
    """
    Keep temperature and sensor status registers updated.

    The task never terminates merely because the DS18B20 is unplugged.
    This keeps the Modbus TCP server alive while exposing the sensor state
    through STATUS_REGISTER.
    """
    last_sensor_state = None

    while True:
        try:
            temp = read_temp()

            if temp is not None:
                value = int(temp * 100)

                context[0].setValues(3, TEMP_REGISTER, [value])
                context[0].setValues(3, STATUS_REGISTER, [1])

                if last_sensor_state is not True:
                    print("[TEMP] DS18B20 sensor connected / available.")

                last_sensor_state = True

                print(
                    f"[TEMP] Temperature: {temp:.2f} °C "
                    f"| Register {TEMP_REGISTER}: {value} "
                    f"| Status: 1"
                )

            else:
                # Do not leave the last valid temperature in the register.
                # The status register is authoritative, but clearing the value
                # prevents old data from looking valid to simple clients.
                context[0].setValues(3, TEMP_REGISTER, [0])
                context[0].setValues(3, STATUS_REGISTER, [0])

                if last_sensor_state is not False:
                    print("[TEMP][WARNING] DS18B20 sensor disconnected / unavailable.")

                last_sensor_state = False

        except Exception as e:
            # A sensor/read error must never kill the background task.
            context[0].setValues(3, TEMP_REGISTER, [0])
            context[0].setValues(3, STATUS_REGISTER, [0])

            print(f"[TEMP][ERROR] Unexpected sensor error: {e}")
            last_sensor_state = False

        await asyncio.sleep(TEMP_UPDATE_INTERVAL_SEC)


async def main():
    write_module_name()

    # Initial state: sensor unavailable until the first successful read.
    context[0].setValues(3, TEMP_REGISTER, [0])
    context[0].setValues(3, STATUS_REGISTER, [0])

    asyncio.create_task(update_temperature_register())

    print("Modbus TCP server running on 0.0.0.0:5020")
    print(f"Register 0: module name ({MODBUS_MODULE_NAME})")
    print("Register 100: temperature * 100")
    print("Register 101: sensor status (1 = OK, 0 = disconnected/error)")

    await StartAsyncTcpServer(
        context=context,
        address=("0.0.0.0", 5020)
    )

if __name__ == "__main__":
    asyncio.run(main())