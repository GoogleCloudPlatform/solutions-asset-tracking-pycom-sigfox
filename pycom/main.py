# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import machine
import network
import uos
import gc
import time
import struct
import socket
import pycom
import binascii
from L76GNSS import L76GNSS
from LIS2HH12 import LIS2HH12
from pytrack import Pytrack
from network import Sigfox


#FALLBACK_CONFIG = "08000a011e000000" # pytrack-example-config.ini
FALLBACK_CONFIG = "010001001e010000" # testing, short timers, no deep sleep
RCZ = Sigfox.RCZ4 # https://build.sigfox.com/sigfox-radio-configurations-rc

def parse_config(hex):
    """Parses and encoded configuration string

    Parameters:
    hex (string): Encoded configuration string

    Returns:
    string:Decoded configuration string

    """
    config = {}
    if len(hex) != 16:
        return
    else:
        hex_b = binascii.unhexlify(hex)
        config["DOWNLINK_HR"] = struct.unpack(">B", hex_b[0:1])[0]
        config["SLEEP_MIN"] = struct.unpack(">H", hex_b[1:3])[0]
        config["DEEP_SLEEP"] = struct.unpack(">B", hex_b[3:4])[0]
        config["GPS_WAIT_SEC"] = struct.unpack(">B", hex_b[4:5])[0]
        config["COMMAND"] = struct.unpack(">B", hex_b[5:6])[0]
        config["RESERVED"] = struct.unpack(">H", hex_b[6:8])[0]
        return c

def blink_led(times):
    """Blinks the onboard LED

    Parameters:
    times (int): How many times to blink the onboard LED

    """
    print("Blinking Locator Indicator LED")
    for i in range(times):
        pycom.rgbled(0xFFFFFF)
        time.sleep(1)
        pycom.rgbled(0x000000)
        time.sleep(1)

def do_command(cmd):
    print(f"Executing *once* command: {cmd}")
    if cmd == 1:
        print("Blinking Locator Indicator LED")
        blink_led(5)
    return


def deep_sleep(py, li, config):
    """Puts the board in sleep mode

    Parameters:
    py: Reference to the device to put in deep sleep
    li: Reference to the 
    config: Reference to the configuration map

    """
    print("Pausing 3s before going to deep sleep...")
    pycom.rgbled(0xFF0000)  # Red
    time.sleep(3)
    # set the acceleration threshold to 2000mG (2G) and the min duration to 200ms
    #li.enable_activity_interrupt(c["ACCEL_MAX_MG"], 200)
    # enable wakeup source from INT pin
    #py.setup_int_pin_wake_up(False)
    # enable activity and also inactivity interrupts, using the default callback handler
    py.setup_int_wake_up(True, True)
    # go to sleep for mins duration if no accelerometer interrupt happens
    py.setup_sleep(config["SLEEP_MIN"] * 60)
    py.go_to_sleep(gps=True)
    return


pycom.heartbeat(False)
pycom.rgbled(0x00FF00)
time.sleep(2)
pycom.rgbled(0x000000)
gc.enable()

py = Pytrack()
l76 = L76GNSS(py, timeout=30)
li = LIS2HH12(py)

# display the reset reason code. Possible values of wakeup reason are:
# WAKE_REASON_POWER_ON = 0
# WAKE_REASON_ACCELEROMETER = 1
# WAKE_REASON_PUSH_BUTTON = 2
# WAKE_REASON_TIMER = 4
# WAKE_REASON_INT_PIN = 8
wake = py.get_wake_reason()
print("Wakeup reason: " + str(wake))

sd = machine.SD()
try:
    os.mount(sd, "/sd")
except OSError:
    print("Unable to mount SD card. Possibly already mounted.")
listdir = os.listdir("/sd")

if "config.txt" in listdir:
    config_file = open("/sd/config.txt", "r")
    config_hex = config_file.readall()
    config_file.close()
    print("Read /sd/config.txt: {}".format(config_hex))
else:
    print("Configuration file: /sd/config.txt missing")
    config_file = open("/sd/config.txt", "w")
    config_file.write("{}".format(FALLBACK_CONFIG))
    config_file.close()
    print("Init /sd/config.txt with defaults: {}".format(FALLBACK_CONFIG))
    config_hex = FALLBACK_CONFIG

config = parse_config(config_hex)
print("Device configuration: {}".format(config))

if "mins_since_dl.txt" in listdir:
    config_file = open("/sd/mins_since_dl.txt", "r")
    mins_since_dl = int(config_file.readall())
    config_file.close()
    print("Read /sd/mins_since_dl.txt: {}".format(mins_since_dl))
else:
    print("Configuration file: /sd/mins_since_dl.txt missing")
    config_file = open("/sd/mins_since_dl.txt", "w")
    config_file.write("0")
    config_file.close()
    print("Init /sd/mins_since_dl.txt with defaults: 0")
    mins_since_dl = 0

# init Sigfox with the correct RCZ
#sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=Sigfox.RCZ4)
sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=RCZ)
# create a Sigfox socket
s = socket.socket(socket.AF_SIGFOX, socket.SOCK_RAW)
# make the socket blocking
s.setblocking(True)

print("Using Sigfox RCZ{}. Frequency range: {}-{} MHz".format(
      RCZ+1, sigfox.frequencies()[0]/1000000,
      sigfox.frequencies()[1]/1000000))

while True:
    if mins_since_dl / 60.0 >= c["DOWNLINK_HR"]:
        print("Sending Downlink request with current configs")
        s.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, True)
        raw = bytearray(binascii.unhexlify(config_hex))
        print("Payload: {} Length: {}B".format(config_hex, len(raw)))
        print("Sending Sigfox DL message. Waiting for reply...")
        pycom.rgbled(0x0000FF)  # Blue
        try:
            s.send(raw)
        except OSError:
            print("OSError. Resetting board")
            time.sleep(5)
            machine.reset()
        downlink_message = s.recv(32)
        pycom.rgbled(0x000000)
        config_hex = binascii.hexlify(downlink_message).format("ascii")
        print("Config HEX received: {}".format(config_hex))
        new_config = parse_config(config_hex)
        if new_config == c:
            print("Received config matches previous one. Ignoring.")
        else:
            c = new_config
            print("Updated device configuration: {}".format(c))
            config_file = open("/sd/config.txt", "w")
            config_file.write("{}".format(config_hex))
            config_file.close()
            print("Wrote: {} to /sd/config.txt".format(config_hex))
            if c["COMMAND"] != 0:
                result = do_command(c["COMMAND"])
        config_file = open("/sd/mins_since_dl.txt", "w")
        config_file.write("0")
        config_file.close()
        print("Reset /sd/mins_since_dl.txt to: 0")
        mins_since_dl = 0
    else:
        s.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, False)
        init_timer = time.time()
        coord = (None, None)
        while coord == (None, None):
            final_timer = time.time()
            diff = final_timer - init_timer
            coord = l76.coordinates()
            if coord == (None, None):
                print("No GPS position. Giving up in {}s".format(c["GPS_WAIT_SEC"] - diff))
                if diff < c["GPS_WAIT_SEC"]:
                    continue
                else:
                    coord = (0, 0)
                    break
        roll = li.roll()
        pitch = li.pitch()
        volt = py.read_battery_voltage()

        b_lat = struct.pack("<f", float(coord[0]))
        b_lng = struct.pack("<f", float(coord[1]))
        b_roll = struct.pack("<B", round(128+((256.0/360.0)*roll)))
        b_pitch = struct.pack("<B", round(128+((256.0/180.0)*pitch)))
        b_volt = struct.pack("<B", round((256.0/5.0)*volt))
        b_wake = struct.pack("<B", wake)

        print("GPS:{} | Roll:{} | Pitch:{} | V:{}".format(coord, roll, pitch, volt))

        raw = bytearray(b_lat) + bytearray(b_lng) + bytearray(b_roll) + \
            bytearray(b_pitch) + bytearray(b_volt) + bytearray(b_wake)
        raw_str = binascii.hexlify(raw).format("utf8")
        print("Payload: {} Length: {}B".format(raw_str, len(raw)))
        print("Sending Sigfox UL message")
        pycom.rgbled(0x0000FF)  # Blue
        try:
            s.send(raw)
        except OSError:
            print("OSError. Resetting board")
            time.sleep(3)
            machine.reset()
        print("Sent Sigfox message")
        pycom.rgbled(0x000000)

    mins_since_dl = mins_since_dl + c["SLEEP_MIN"]
    config_file = open("/sd/mins_since_dl.txt", "w")
    config_file.write("{}".format(mins_since_dl))
    config_file.flush()
    config_file.close()
    print("Wrote: {} to /sd/mins_since_dl.txt".format(mins_since_dl))

    if c["DEEP_SLEEP"] == 1:
        os.unmount("/sd")
        print("Starting {}min deep sleep".format(c["SLEEP_MIN"]))
        deep_sleep(py, li, c)
    else:
        print("Starting {}min normal sleep".format(c["SLEEP_MIN"]))
        time.sleep(c["SLEEP_MIN"] * 60)
