## Introduction

In order to understand what the PDM microphone capture and how it's the quality of the audio captured, you can use the [pdm_serial.py](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/master/python_receiver/pdm_serial.py) script to listen for some seconds and save the result in a `wav` file. I give here my recording example named _microphone-reults.wav_.

Make sure to install `scipy` and `numpy`.

## The recognizer script

Samples from Arduino Nano 33 BLE sense PDM microphone arrive at 16KHz of sample rate and are 16 bit per sample.
The PDM code will fill a buffer of 512 samples, 16 bit each. This buffer is then passed to `Serial.write()` which will write 1024 bytes and then start to refill the same buffer for the  next burst. 
So in order to count record for the required seconds, we read 'fsamp' * 'seconds' transactions and put them in the numpy buffer.  
Actually, we read 1024 bytes each time and converting them into a numpy array of 512 items with size `numpy.int16`. So it's easier to think in bytes and approximate the seconds of listening.

Then we send the data to Wit.Ai and the received string is used to search for matching keywords and decide what to to with the bedroom light. The light is controlled through a Shelly Plus 1 relay connected to a MQTT broker on a Raspberry pi 4 where also the recognizer script run (through systemctl scheduled worker).

## Required packages

Import the required packages in your Python environment. The package used are:

* [Pyserial](https://github.com/pyserial/pyserial) master branck (`pip install git+https://github.com/pyserial/pyserial`)
* [Pyserial asyncio fast](https://github.com/home-assistant-libs/pyserial-asyncio-fast) because is more up to date (`pip install git+https://github.com/home-assistant-libs/pyserial-asyncio-fast`)
* Numpy
* [Speech Recognition](https://pypi.org/project/SpeechRecognition/)
* [Paho MQTT](https://pypi.org/project/paho-mqtt/)


