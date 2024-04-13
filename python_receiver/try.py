#!/home/tito/venv/bin/python

import asyncio
import serial
import serial_asyncio_fast
import numpy as np
from scipy.io import wavfile
import math
import sys
import speech_recognition as sr
import time
import os
from threading import Event
from threading import Thread
from queue import Queue
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish



# Prepare the buffer to put into wav file
y = np.array([], np.int16)
z = np.array([], np.int16)

# Serial COMM
serial_port = "<COM or /dev/tty>"

# Threading controls
audio_queue = Queue()
event = Event()

# MQTT
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
broker_url = "localhost"
shelly_id = "<shelly id>"

# Speech recognition variable
r = sr.Recognizer()
engine_KEY = "<Wit.Ai KEY>"
matches_on = ["cendi", "luc"]
matches_off = ["egni", "luc"]

# Signal processing variables
bufsize = 256 * 2   # It's the size of the numpy array 'x'
seconds_to_reset = 200 
conversion = 32     # 32 conversion * 512 bufsize == 1 second at 16KHz of sample rate (almost)
fsamp = 16000
N = seconds_to_reset * conversion * bufsize     # == [seconds] of recording (almost)
samp = False
i = 0
listening_for = 3   # * conversion == [second/bufsize]
trigger_volume = 23000      # If the audio samples have magnitude greater than this start listening



# Serial protocol callbacks
class InputChunkProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        # Create numpy buffer
        global conversion
        global listening_for
        global y
        global samp
        global i
        global z
        global trigger_volume

        # Data in input is buffered as 16bit, so 512 bytes are coming at burst
        x = np.frombuffer(data, np.int16)

        # Continuous data recording
        y = np.append(y, x, axis=0)

        #### Run to completion state machine, non blocking

        if x.max(0) > trigger_volume and not samp:
            # Too loud, start listening for <listening_for>
            samp = True

        if samp == True and i <= listening_for * conversion:
            # Collect also the second before the activation
            if i == 0 and y.size > conversion * x.size: z = np.append(z, y[-(conversion + 1) * x.size:-x.size], axis=0)
            z = np.append(z, x, axis=0)
            i += 1

        # Use >= to be sure to enter in this state
        if z.size >= (x.size * (listening_for + 1) * conversion) and i >= listening_for * conversion:
            # Send to speech recognizer thread and reset 
            audio_queue.put(z)
            z = np.array([], np.int16)
            samp = False
            i = 0

        if y.size >= N and not samp:
            # Keep the last half of the background recording
            y = np.delete(y, np.s_[math.ceil(-y.size/2)-1::-1], 0)

        # stop callbacks again immediately
        self.pause_reading()

    def pause_reading(self):
        # This will stop the callbacks to data_received
        self.transport.pause_reading()

    def resume_reading(self):
        # This will start the callbacks to data_received again with all data that has been received in the meantime.
        self.transport.resume_reading()

       
# Serial communcation task
async def reader(): 
    transport, protocol = await serial_asyncio_fast.create_serial_connection(loop, InputChunkProtocol, serial_port, baudrate=115200)

    while not transport.is_closing() and event.is_set():
        await asyncio.sleep(0.01)   # Cooperative multitasking done right ;)
        protocol.resume_reading()
    


# Speech_recognition thread
def recognize_worker():

    while True:
        audio = sr.AudioData(audio_queue.get(), fsamp, 2)  # retrieve the next audio processing job from the main thread
        if audio is None: break  # stop processing if the main thread is done

        voice = ''
        
        # recognize speech using Wit.ai
        WIT_AI_KEY = engine_KEY  # Wit.ai keys are 32-character uppercase alphanumeric strings
        try:
            voice = str(r.recognize_wit(audio, key=WIT_AI_KEY)).lower()         
        except sr.UnknownValueError:
            print("Wit.ai could not understand audio")
        except sr.RequestError as e:
            print("Could not request results from Wit.ai service; {0}".format(e))
        except:
            continue
        else:
            if voice != '':
                if all(x in voice for x in matches_on): publish.single(topic=shelly_id+"/command/switch:0", payload="on", qos=2)
                elif all(x in voice for x in matches_off): publish.single(topic=shelly_id+"/command/switch:0", payload="off", qos=2)
        


# MQTT callbacks
def on_connect(mqttc, obj, flags, reason_code, properties):
    print("reason_code: " + str(reason_code))

def on_message(mqttc, obj, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

def on_subscribe(mqttc, obj, mid, reason_code_list, properties):
    print("Subscribed: " + str(mid) + " " + str(reason_code_list))

def on_log(mqttc, obj, level, string):
    print(string)



# Main loop
while True:

    try:
        event.set()
        
        mqttc.on_message = on_message
        mqttc.on_connect = on_connect
        mqttc.on_subscribe = on_subscribe
        mqttc.connect(broker_url)   # Blocking call
        mqttc.subscribe(topic=shelly_id+"/status/switch:0", qos=2)
        mqttc.loop_start()  # It won't block, the loop is on another thread (the 3rd!)

        # Start a new thread to recognize audio, while this thread focuses on listening
        recognize_thread = Thread(target=recognize_worker)
        recognize_thread.daemon = True
        recognize_thread.start()

        # Listening on the main thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(reader())  

        # If reader stopped not by the user 
        audio_queue.put(None)
        event.clear()
        mqttc.disconnect()
        time.sleep(1)
        mqttc.loop_stop()
        loop.close()
        audio_queue = Queue()
        time.sleep(5)
    
    except KeyboardInterrupt:

        print("Exiting...")
        event.clear()
        audio_queue.put(None)
        mqttc.disconnect()
        time.sleep(3)
        mqttc.loop_stop()
        loop.close()
        break

    except serial.SerialException:

        audio_queue.put(None)
        event.clear()
        mqttc.disconnect()
        time.sleep(1)
        mqttc.loop_stop()
        loop.close()
        audio_queue = Queue()
        time.sleep(5)

