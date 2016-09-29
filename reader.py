import time
import machine
import onewire, ds18x20
import ujson
import ubinascii

ONEWIREPIN = 5

def gettimestr():
    curtime=rtc.datetime()
    _time="%04d" % curtime[0]+ \
          "%02d" % curtime[1]+ \
          "%02d" % curtime[2]+" "+ \
          "%02d" % curtime[4]+ \
          "%02d" % curtime[5]
    return _time

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
_time=gettimestr()
for rom in roms:
    print("topic "+config['MQTT_TOPIC']+ubinascii.hexlify(rom).decode())
    print(_time)
    print(ds.read_temp(rom))
