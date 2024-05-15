## Speech Recognition with Wit.AI :ear: + 	:microphone:

Given that the Arduino Nano 33 BLE Sense is built on [Mbed OS](https://os.mbed.com/mbed-os/) and features an analog-to-digital frontend from a [microphone](https://docs.arduino.cc/tutorials/nano-33-ble-sense/microphone-sensor/) via a PDM-to-PCM chain to memory through DMA transfers (see the [nrf52840](https://infocenter.nordicsemi.com/topic/ps_nrf52840/pdm.html?cp=5_0_0_5_14) documentation), I've used the default RTOS thread to capture microphone input and send audio samples to a Python receiver for processing. The [receiver](https://github.com/TIT8/BLE-sensor_PDM-microphone/tree/master/python_receiver) will respond to voice commands by controlling the light in my bedroom, turning it on and off accordingly.

_All of this while also sending data to connected BLE devices (using another RTOS thread)._ :rocket:

## Humidity Sensor via BLE :radio:

I'm beginning to grasp concepts like RSSI and advertising, services and characteristics, default and custom UUIDs, GAP and GATT, as well as peripheral/server and central/client roles in Bluetooth Low Energy, all through the lens of the [Arduino Nano 33 BLE Sense](https://docs.arduino.cc/hardware/nano-33-ble-sense/).

Here, I'm utilizing the [Notify](https://community.nxp.com/t5/Wireless-Connectivity-Knowledge/Indication-and-Notification/ta-p/1129270) feature of BLE, reminiscent of pub-sub protocols like MQTT. Referencing the [Arduino documentation](https://docs.arduino.cc/tutorials/nano-33-ble/bluetooth/) and the specifications outlined for the [Environmental Sensing Service](https://www.bluetooth.com/specifications/specs/environmental-sensing-service-1-0/) 📡 can provide further insight.

Every time the humidity change at least of 1%, new data are written on the BLE Characteristic and different devices can access the values.

_What better way to learn something new than with Arduino?_ 💪

## Mbed OS Structure

<ins>Two threads are employed: one for BLE and another for PDM</ins>. The PDM thread is assigned the highest priority and exclusively utilizes the Serial, preventing access from the BLE thread (though this is unnecessary for proper operation).

I've opted to run the PDM task within the main loop provided by the Arduino framework (at `osPriorityNormal`), while the BLE task operates on a separate thread at `osPriorityBelowNormal`. Leveraging the [CMSIS-RTOS abstraction API](https://os.mbed.com/docs/mbed-os/v6.16/apis/thread.html) provided by Mbed enables priority configuration. Additionally, before the main loop restarts, control is yielded to the scheduler to ensure proper execution (the default RTOS tick frequency is 1kHz).

Internally, the PDM library employs a circular buffer, which is repeatedly copied into the user's [sample buffer](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/51feb5f0b0abefecbba297cffd588a23114bfa25/src/main.cpp#L22), subsequently copied into the `Serial` buffer (Arduino-Mbed's Serial API utilizes the [Async Writer](https://github.com/arduino/ArduinoCore-mbed/blob/2d27acf719a2092f161c0e521c7521fb4dd1a0b7/cores/arduino/USB/USBCDC.cpp#L43) class, ensuring that each `Serial.write` call saves the buffer dynamically into a separate memory space, mitigating concerns about timing discrepancies between microphone ADC and Serial writing, see [here](https://forum.arduino.cc/t/time-taken-for-serial-write-function-in-arduino-using-atmega2560-chip-with-baud-rate-115200/1165817/2) for more).   
I decided not to process incoming data from the ADC/DMA on the Arduino Nano (explained [here](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/c0054982ad5301c289135aaf45ffbabf6eb57034/src/main.cpp#L91)), but perhaps I can try it in the future. This would reduce the load on the CPU that receives data over Serial since serial communication would be less utilized, but it would increase the CPU usage on the nrf52 and stress the constrained SRAM.

A [Python script](https://github.com/TIT8/BLE-sensor_PDM-microphone/tree/master/python_receiver) is employed to receive and process the samples, generating an audio file, interfacing with [***Wit.AI***](https://wit.ai/), and controlling the bedroom light as demonstrated in a [previous project](https://github.com/TIT8/shelly_esp32_button_espidf) upon detection of specific keywords. Also, take a look at the [Go program](https://github.com/TIT8/BLE-sensor_PDM-microphone/tree/master/golang_receiver), with its astonishingly simple concurrent model. I've achieved significant efficiency improvement (0.5% of average CPU load) using it.

## References

[Here](https://dumblebots.com/2020/04/06/programming-with-mbed-on-arduino/), you can find my initial reference for using Mbed OS with Arduino, and [here](https://forums.mbed.com/t/audio-input-isnt-working-correctly/23024) is the forum where you can ask questions (this link will actually take you to an issue that I found interesting to illustrate the simplicity of Mbed OS).

If you don't know what an operating system does, [this video](https://www.youtube.com/watch?v=TEq3-p0GWGI) is for you.

### Requirements

* [Arduino Nano 33 BLE Sense](https://docs.arduino.cc/hardware/nano-33-ble-sense/) or similar ([nRF52840](https://content.arduino.cc/assets/Nano_BLE_MCU-nRF52840_PS_v1.1.pdf)).
* [PlatformIO](https://platformio.org/) (easily adaptable to other environments).
* [ArduinoBLE](https://github.com/arduino-libraries/ArduinoBLE) library.
* [Arduino_HTS221](https://github.com/arduino-libraries/Arduino_HTS221) library.
* Hardware capable of running Python connected to a serial port.

## How to test the BLE task?

Utilize [nRF Connect](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile) on a smartphone, a [Python script](https://github.com/TIT8/BLE-sensor_PDM-microphone/tree/master/python_test_ble) on PC/MAC, or an [ESP32](https://github.com/TIT8/BLE_esp32) if available.   
And, by the way, no, I'm not sending float directly, but remember this [discussion](https://forum.arduino.cc/t/passing-float-values-with-bluetooth/656814) and this [example](https://github.com/adafruit/Adafruit_BluefruitLE_nRF51/blob/master/examples/healththermometer/IEEE11073float.cpp) in the future.

<img src="https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/3d87bad1-526b-4154-853f-053570986b97" width="200" height="400">
<img src="https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/3756ee05-ef1f-484b-94cd-6b1e372609d2" width="200" height="400">


## Pros and cons of speech recognition task

➕ This approach is working very well: collecting audio samples, sending them to a serial device that manages the connection with the Wit.Ai API and takes action based on the transcribed text. The Wit.Ai AI performs incredibly well, being trained by Meta, and **you could also train it to better recognize your keywords**. So it's very reliable. 

➖/➕ However, latency remains the primary concern. For instance, when I say "accendi luce," it takes 1-2 seconds before the light turns on (although, without errors, it consistently does turn on! :mechanical_arm:). Nevertheless, from my testing, it executes actions so swiftly that I hesitate to consider it slow. As with any system dealing with human-time-asynchronous events/inputs, there's little that can be done to further reduce the action time.

➖ Data privacy is a concern; hence, <ins>the Python receiver I developed sends data to the Wit.Ai API only when the captured audio reaches a sufficiently high volume</ins> (as intended, I'm talking to the Arduino with a certain level which I don't use with my brother in the room normally), rather than through continuous streaming.

The two minus can be improved in two ways: if you desire low latency and quick responses to voice input, you need to move the inference/transcribing part onto the device, either the host of the serial connection or the Arduino Nano 33 BLE Sense.

1)  The best alternative I've achieved with success is hosted on [Github](https://github.com/TIT8/shelly_button_esp32_arduino/tree/master/speech_recognition), thanks to [Edge Impulse](https://edgeimpulse.com/) for rapid prototyping. The speech recognition process run on the nrf52840. However, upon reviewing [their documentation](https://docs.edgeimpulse.com/docs/tutorials/advanced-inferencing/continuous-audio-sampling) and the generated code, I realize I can learn more (and perhaps borrow :zany_face:) about offline voice recognition. This is a completely different approach, offering more privacy and faster responses, but achieving reliability requires a significant amount of time to train the model for inference, and the results are slightly inferior to "Wit.Ai + Python."

2) An intermediate solution could be to maintain the speech recognition on external hardware instead of the nRF52840, utilizing an offline speech recognition engine such as [PocketSphinx](https://pocketsphinx.readthedocs.io/en/latest/) (tested and not working, I'm still a beginner) or [Vosk](https://github.com/alphacep/vosk-api) (although it's a bit tricky to get started with, this [demo](https://github.com/anuran-roy/vosk-demo) can be helpful, **though it hasn't proven entirely reliable in my tests**). But I think that transcriptor as good as Wit.Ai are difficult to find for this application, at least for the italian language. ***And there is a big [BUT](https://github.com/TIT8/BLE-sensor_PDM-microphone/tree/master/python_receiver#be-careful-with-timeouts) if you want to use this solution with my Python-receiver code***. Actually, this solution can increase latency if you don't have proper hardware.

So, life is full of trade-offs. We're lucky to have more than one solution :lying_face:.


### Goals 😎

* Direct use of the [official nRF SDK](https://www.nordicsemi.com/Products/Development-software/nRF-Connect-SDK).
* Learn more about Mbed OS (coming from FreeRTOS, I'm flabbergasted by how good it is) ❤️
* Attempting to replicate functionality on ESP32 via ESP-IDF BLE library. &nbsp; [[DONE ✔️]](https://github.com/TIT8/BLE_esp32)
* ***Offline speech recognition via a pre-trained machine learning model using Tensorflow (TinyML).*** &nbsp; [[Started :construction_worker:]](https://github.com/TIT8/shelly_button_esp32_arduino/tree/master/speech_recognition)
