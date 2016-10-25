import time
import machine
import network
import onewire, ds18x20
import ujson
import ubinascii
from umqtt.simple import MQTTClient
import ntptime

def gettimestr():
    rtc=machine.RTC()
    curtime=rtc.datetime()
    _time="%04d" % curtime[0]+ "%02d" % curtime[1]+ "%02d" % curtime[2]+" "+ "%02d" % curtime[4]+ "%02d" % curtime[5]
    return _time

#check if gpio4 is pulled down
stoppin = machine.Pin(4,mode=machine.Pin.IN,pull=machine.Pin.PULL_UP)
if stoppin.value()==0:
    print("Pin down, stop")
else:
    #normal loop

    f = open('config.json', 'r')
    config = ujson.loads(f.readall())

    # the device is on GPIOxx
    ONEWIREPIN = config['ONEWIREPIN']
    dat = machine.Pin(ONEWIREPIN)

    # create the onewire object
    ds = ds18x20.DS18X20(onewire.OneWire(dat))

    # scan for devices on the bus
    roms = ds.scan()
    print('found devices:', roms)

    #print('temperatures:', end=' ')
    ds.convert_temp()
    time.sleep_ms(750)

    # Check if we have wifi, and wait for connection if not.
    wifi = network.WLAN(network.STA_IF)
    while not wifi.isconnected():
        print(".")
        time.sleep(1)

    ntptime.settime()
    _time=gettimestr()
    c = MQTTClient("umqtt_client", config['MQTT_BROKER'])
    c.connect()

    #check battery voltage?
    if (config['MEASURE_VOLTAGE']):
        adc = machine.ADC(0)
        voltage = adc.read();
        topic="/hardware/"+machine.unique_id().decode()+"/voltage/"
        message=_time+" "+str(voltage)
        c.publish(topic,message)

    #loop ds18b20 and send results to mqtt broker
    for rom in roms:
        print("topic "+config['MQTT_TOPIC']+ubinascii.hexlify(rom).decode())
        topic=config['MQTT_TOPIC']+ubinascii.hexlify(rom).decode()
        print(_time)
        print(ds.read_temp(rom))
        message=_time+' '+str(ds.read_temp(rom))
        c.publish(topic,message)

    c.disconnect()
