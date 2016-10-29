import time
import machine
import network
import onewire, ds18x20
import ujson
import ubinascii
from umqtt.simple import MQTTClient
import ntptime
import errno

#Thrown if an error that is fatal occurs,
#stop measurement cycle.
class Error(Exception):
    pass

#Thrown if an error that is not fatal occurs,
#goes to deep sleep and continues as normal.
#For example no wifi connection at this time.
class Warning(Exception):
    pass
    
def gettimestr():
    rtc=machine.RTC()
    curtime=rtc.datetime()
    _time="%04d" % curtime[0]+ "%02d" % curtime[1]+ "%02d" % curtime[2]+" "+ "%02d" % curtime[4]+ "%02d" % curtime[5]
    return _time

def deepsleep():
    # configure RTC.ALARM0 to be able to wake the device
    rtc = machine.RTC()
    rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)

    # set RTC.ALARM0 to fire after 60 seconds (waking the device)
    rtc.alarm(rtc.ALARM0, 60000)

    # put the device to sleep
    machine.deepsleep()

#check if gpio4 is pulled down
stoppin = machine.Pin(4,mode=machine.Pin.IN,pull=machine.Pin.PULL_UP)
if stoppin.value()==0:
    print("Pin down, stop")
else:
    try:
        #normal loop

        try:
            f = open('config.json', 'r')
            config = ujson.loads(f.readall())
        except OSError as e:
            if e.args[0] == errno.MP_ENOENT or e.args[0] == errno.MP_EIO:
                print("I/O error({0}): {1}".format(e.args[0], e.args[1]))
                raise Error

        # the device is on GPIOxx
        ONEWIREPIN = config['ONEWIREPIN']
        dat = machine.Pin(ONEWIREPIN)

        # create the onewire object
        ds = ds18x20.DS18X20(onewire.OneWire(dat))

        # scan for devices on the bus
        roms = ds.scan()
        print('found devices:', roms)
        if (len(roms)>0):
            ds.convert_temp()
            time.sleep_ms(750)

        # Check if we have wifi, and wait for connection if not.
        print("Check wifi connection.")
        wifi = network.WLAN(network.STA_IF)
        i = 0
        while not wifi.isconnected():
            if (i>10):
                print("No wifi connection.")
                raise Warning
            print(".")
            time.sleep(1)
            i=i+1

        try:
            print("Get time.")
            ntptime.settime()
        except OSError as e:
            if e.args[0] == errno.ETIMEDOUT: #OSError: [Errno 110] ETIMEDOUT
                print("Timeout error, didn't get ntptime.")
                #if we did not wake up from deep sleep
                #we cannot continue until we get correct time
                if (machine.reset_cause()!=machine.DEEPSLEEP):
                    raise Warning
            if e.args[0] == -2: #OSError: dns error
                print("DNS error, didn't get ntptime.")
                #if we did not wake up from deep sleep
                #we cannot continue until we get correct time
                if (machine.reset_cause()!=machine.DEEPSLEEP):
                    raise Warning
            else:
                raise
        _time=gettimestr()
                

        print("Open MQTT connection.")
        c = MQTTClient("umqtt_client", config['MQTT_BROKER'])
        c.connect()

        #check battery voltage?
        if (config['MEASURE_VOLTAGE']):
            adc = machine.ADC(0)
            voltage = adc.read();
            topic="/hardware/"+ubinascii.hexlify(machine.unique_id()).decode()+"/voltage/"
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

        deepsleep()
    except Warning:
        deepsleep()
    except Error:
        print("Error({0}): {1}".format(e.args[0], e.args[1]))
    
