#!/home/tito/venv/bin/python

import serial
import signal
import sys
import wave
import numpy as np
from scipy.io import wavfile
import speech_recognition as sr
import time
from threading import Thread
from queue import Queue


'''
This script take the Arduino-Nano-33-BLE-sense-PDM-mic data in and save them on a wavfile
'''


# Serial Config
ser = serial.Serial(port='<COM or /dev/tty/>',baudrate=115200,bytesize=8,timeout=.1)
ser.reset_input_buffer()
ser.reset_output_buffer()

# Digital signal parameter
fsamp   = 16000        
seconds = 10
N = seconds * fsamp     # Number of samples to record

# Variables
x = bytearray()

# Recording
for i in range(N):
    x.extend(ser.read(2))   # Read 2 bytes at burst, so 1 sample

# Convert buffer in numpy array
y = np.frombuffer(x, np.int16)

# Stop Streaming
ser.reset_input_buffer()
ser.reset_output_buffer()
ser.close()


# Wav file created or modified
wavname  = 'microphone-results.wav'

# Save Recorded Audio
wavfile.write(wavname, fsamp, np.asarray(y, np.int16))

# Another save method
'''
# write audio to a WAV file
audio = sr.AudioData(x, fsamp, 2)

with open("microphone-results.wav", "wb") as f:
    f.write(audio.get_wav_data())
'''

# Oh look, another save method
'''
with wave.open('file.wav', "wb") as wav:
    wav.setframerate(fsamp)
    wav.setnchannels(1)
    wav.setsampwidth(2)     # 2 because of 16 bit samples, 2 * 8 bit
    wav.writeframes(x)
'''

# You know what this do
'''
with sr.AudioFile(wavname) as source:
    audio = r.record(source)  # read the entire audio file
'''

print(f"Recording saved to file: {wavname}")