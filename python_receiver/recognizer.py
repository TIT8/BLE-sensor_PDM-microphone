#!/home/tito/venv/bin/python

import asyncio
import serial
import serial_asyncio_fast
import numpy as np
import math
import speech_recognition as sr
import time
import glob
import signal
import os
import sys
import subprocess
from threading import Event
from threading import Thread
from queue import Queue
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import uvloop



'''
    Global variables
'''

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())    # Only for Linux

# Threading controls
audio_queue = Queue()
event = Event()
stop = Event()

# MQTT
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
shelly_id = "<shelly id>"   # Given on MQTT section of the Internet section in the setting of the Shelly Device




'''
    Receiver task (will run in its own executor)
'''
async def receiver(loop, serial_port_ACM):

    global audio_queue
    global event 
    global stop

    # Serial COMM
    baudrate = 115200

    # Signal processing variables
    bufsize = 512   # It's the size of the numpy array 'x'
    seconds_to_reset = 200
    conversion = 32     # 32 conversion * 512 bufsize == 1 second at 16KHz of sample rate (almost)
    N = seconds_to_reset * conversion * bufsize     # == [seconds] of recording (almost)
    samp = False
    i = 0
    n = 0
    listening_for = 1.5   # * conversion == [second/bufsize]
    trigger_volume = 17000  # If the audio samples have magnitude greater than this start listening

    # Preparing buffers
    y = np.zeros(int(N), np.int16)
    z = np.zeros(int((listening_for + 1) * conversion * bufsize), np.int16)
    t = np.zeros(int(listening_for * conversion * bufsize), np.int16)
    
    try:
        reader, writer = await serial_asyncio_fast.open_serial_connection(url=serial_port_ACM, baudrate=baudrate)
        print(writer.transport.get_extra_info("serial"))
    except:
        print("Problem with serial connection")
        writer = None
        event.clear()
        

    while event.is_set() and not stop.is_set():
    
        deadline = loop.time() + 2    # Timeout of two seconds
        try:
            async with asyncio.timeout_at(deadline):
                data = await reader.readexactly(bufsize * 2)    # In order to read 512 samples of 16 bit each, I need 1024 bytes
        except:
            print("Maybe a timeout, closing...")
            break

        # Data in input is buffered as 16bit, so 1024 bytes are coming at burst
        x = np.frombuffer(data, np.int16)
        # Continuous data recording
        y[n * bufsize: (n+1) * bufsize] = x

        '''
            Run to completion state machine, non blocking
        '''
        if x.max(0) >= trigger_volume and not samp:
            # Too loud, start listening for <listening_for>
            samp = True

        if samp == True: 
            # Listen and collect data
            if i < listening_for * conversion:
                # Collect also the second before the activation
                if i == 0:
                    if n >= conversion: z[:bufsize * conversion] = y[(n - conversion) * bufsize: n * bufsize]
                    else: z[:bufsize * conversion] = np.roll(y,conversion*bufsize,0)[n * bufsize: (n+conversion) * bufsize]
                t[i * bufsize: (i+1) * bufsize] = x
                i += 1

            # Use >= to be sure to enter in this state
            if i >= listening_for * conversion:
                # Send to speech recognizer thread and reset 
                z[bufsize * conversion:] = t
                samp = False
                i = 0
                audio_queue.put(z)

        if n < conversion * seconds_to_reset - 1:
            n += 1
        else:
            n = 0

    if writer is not None:
        writer.transport.abort()    # Safe release of the serial communication port
        await asyncio.sleep(1)
    
    await asyncio.sleep(1)
    print("Exiting coroutine")      # Stopping the loop

  


'''
    Speech recognition thread
'''
def recognize_worker():

    global mqttc

    # Audio variables
    global audio_queue
    global shelly_id
    fsamp = 16000

    # Speech recognition variable
    r = sr.Recognizer()
    engine_KEY = "<Wit.Ai KEY>"     # Set the Wit.Ai key, you must register to their services
    matches_on = ["accend", "luc"]
    matches_off = ["spegn", "luc"]
    
    print("Starting recognizer worker")
    
    while True:
        audio_sample = audio_queue.get()
        if audio_sample is None: break

        audio = sr.AudioData(audio_sample, fsamp, 2)  # retrieve the next audio processing job from the main thread
        voice = ''
        
        # recognize speech using Wit.ai
        WIT_AI_KEY = engine_KEY  # Wit.ai keys are 32-character uppercase alphanumeric strings
        try:
            voice = str(r.recognize_wit_new(audio, key=WIT_AI_KEY)).lower()         
        except sr.UnknownValueError:
            print("Wit.ai could not understand audio")
        except sr.RequestError as e:
            print("Could not request results from Wit.ai service; {0}".format(e))
        except:
            continue
        else:
            if voice != '':
                if all(x in voice for x in matches_on): mqttc.publish(topic=shelly_id+"/command/switch:0", payload="on", qos=2)
                elif all(x in voice for x in matches_off): mqttc.publish(topic=shelly_id+"/command/switch:0", payload="off", qos=2)

    print("Exiting recognizer worker")



'''
    Find serial port where PDM MIC is attached (look here for alternative https://github.com/pyserial/pyserial/pull/658/files)
'''
def serial_ports():
    # Lists serial port names
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result




'''
    Closing the asyncio loop and stopping other threads for safe exit, releasing the serial connection
'''
def ask_exit():
    global audio_queue
    global event
    global stop
    global mqttc

    event.clear()           # Stop coroutine
    audio_queue.put(None)   # Stop the recognizer worker
    stop.set()              # Gracefully stop the loop and all other asyncio task in background
    time.sleep(1)
    mqttc.disconnect()      # Stop the MQTT loop on the other thread
    mqttc.loop_stop()
    print("Exiting...")




'''
    MQTT section
'''
# MQTT init
def mqttc_init():
    global mqttc
    broker_url = "localhost"    # Default, you can change it to the IP address your broker
    global shelly_id
    
    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_subscribe = on_subscribe
    mqttc.connect(broker_url)   # Blocking call, default port 1883
    mqttc.subscribe(topic=shelly_id+"/status/switch:0", qos=2)
    mqttc.loop_start()  # It won't block, the loop is on another thread (the 3rd!)


# MQTT callbacks
def on_connect(mqttc, obj, flags, reason_code, properties):
    print("reason_code: " + str(reason_code))

def on_message(mqttc, obj, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

def on_subscribe(mqttc, obj, mid, reason_code_list, properties):
    print("Subscribed: " + str(mid) + " " + str(reason_code_list))

def on_log(mqttc, obj, level, string):
    print(string)




''' 
    Speech_recognition thread init
'''
def rec_worker_init():
    # Start a new thread to recognize audio, while this thread focuses on listening
    recognize_thread = Thread(target=recognize_worker)
    recognize_thread.daemon = True
    recognize_thread.start()
    



'''
    Main loop
'''
def loop():
    global event
    global audio_queue
    global stop
    
    while True:

        event.set()
        
        serial_port = ''
        for serial_port_name in serial_ports():
            if "ACM" in serial_port_name:
                serial_port = serial_port_name
                
        subprocess.run(["fuser", "-k", serial_port])    # Kill process that are using the MIC, if any
        time.sleep(1)   # Give the OS time to start other services
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
            
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, ask_exit)      # Handle external signal, also SIGTERM from OS

        try:
            loop.run_until_complete(receiver(loop, serial_port))
        except:
            pass

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(sig)

        while not audio_queue.empty():
            audio_queue.get()           # Empty the queue to restart listening wihtout interfering with old samples

        time.sleep(2)
        loop.close()

        if stop.is_set():
            break  




def main():
    global stop
    stop.clear()
    
    mqttc_init()
    rec_worker_init()
    loop()


if __name__ == "__main__":
    main()
    print("Service stopped")    # If read on the systemctl status log mean "the script stopped gracefully"
