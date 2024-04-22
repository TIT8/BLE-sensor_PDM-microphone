## Introduction

To comprehend the functionality of the PDM microphone and evaluate the quality of the captured audio, you can utilize the [pdm_serial.py](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/master/python_receiver/pdm_serial.py) script to listen for a few seconds and save the results in a `wav` file. In the repo there is an example recording named _microphone-results.wav_.

Ensure that you have `scipy` and `numpy` installed.

## The Recognizer Script

Samples from the Arduino Nano 33 BLE Sense PDM microphone arrive at a sample rate of 16 kHz and are 16 bits per sample. The PDM code fills a buffer of 512 samples, each 16 bits. This buffer is then passed to `Serial.write()`, which writes 1024 bytes and proceeds to refill the same buffer for the next burst. Therefore, to record for the desired duration, we read 'fsamp' * 'seconds' transactions and store them in the numpy buffer. Essentially, we read 1024 bytes each time and convert them into a numpy array of 512 items with a size of `numpy.int16`. Hence, it's more convenient to think in terms of bytes to approximate the listening duration.

Subsequently, we transmit the data to Wit.Ai, and the received string is utilized to search for matching keywords, determining the action to be taken with the bedroom light. The light is controlled through a Shelly Plus 1 relay connected to an MQTT broker on a Raspberry Pi 4, where the recognizer script also runs (via a scheduled worker in systemctl).

:monocle_face: &nbsp; Read the [code](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/master/python_receiver/recognizer.py) please.

## Required Packages

Import the necessary packages into your Python environment. The packages used are:

* [Pyserial](https://github.com/pyserial/pyserial) master branch (`pip install git+https://github.com/pyserial/pyserial`)
* [Pyserial asyncio fast](https://github.com/home-assistant-libs/pyserial-asyncio-fast) because it is more up-to-date (`pip install git+https://github.com/home-assistant-libs/pyserial-asyncio-fast`)
* Numpy
* [Speech Recognition](https://pypi.org/project/SpeechRecognition/)
* [Paho MQTT](https://pypi.org/project/paho-mqtt/)

## References

[Excellent example of using Pyserial with AsyncIO](https://tinkering.xyz/async-serial/) :yum:
