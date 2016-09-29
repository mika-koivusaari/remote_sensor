import time
import machine
import onewire, ds18x20
import ujson
import ubinascii

ONEWIREPIN = 5

f = open('config.json', 'r')
config = ujson.loads(f.readall())

# the device is on GPIOxx
dat = machine.Pin(ONEWIREPIN)

# create the onewire object
ds = ds18x20.DS18X20(onewire.OneWire(dat))

# scan for devices on the bus
roms = ds.scan()
print('found devices:', roms)

#print('temperatures:', end=' ')
ds.convert_temp()
time.sleep_ms(750)
for rom in roms:
    print("topic "+config['MQTT_TOPIC']+ubinascii.hexlify(rom).decode())
    print(ds.read_temp(rom))
