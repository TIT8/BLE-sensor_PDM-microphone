## Speech Recognition with Wit.AI :ear: + 	:microphone:

Given that the Arduino Nano 33 BLE Sense is built on [Mbed OS](https://os.mbed.com/mbed-os/) and features an analog-to-digital frontend from a [microphone](https://docs.arduino.cc/tutorials/nano-33-ble-sense/microphone-sensor/) via a PDM-to-PCM chain to memory through DMA transfers (see the [nrf52840](https://infocenter.nordicsemi.com/topic/ps_nrf52840/pdm.html?cp=5_0_0_5_14) documentation), I've used the default RTOS thread to capture microphone input and send audio samples to a Python receiver for processing.

_All of this while also sending data to connected BLE devices (using another RTOS thread)._ :rocket:

## Humidity Sensor via BLE :radio:

I'm beginning to grasp concepts like RSSI and advertising, services and characteristics, default and custom UUIDs, GAP and GATT, as well as peripheral/server and central/client roles in Bluetooth Low Energy, all through the lens of the [Arduino Nano 33 BLE Sense](https://docs.arduino.cc/hardware/nano-33-ble-sense/).

Here, I'm utilizing the [Notify](https://community.nxp.com/t5/Wireless-Connectivity-Knowledge/Indication-and-Notification/ta-p/1129270) feature of BLE, reminiscent of pub-sub protocols like MQTT. Referencing the [Arduino documentation](https://docs.arduino.cc/tutorials/nano-33-ble/bluetooth/) and the specifications outlined for the [Environmental Sensing Service](https://www.bluetooth.com/specifications/specs/environmental-sensing-service-1-0/) 📡 can provide further insight.

_What better way to learn something new than with Arduino?_ 💪

## Mbed OS Structure

<ins>Two threads are employed: one for BLE and another for PDM</ins>. The PDM thread is assigned the highest priority and exclusively utilizes the Serial, preventing access from the BLE thread (though this is unnecessary for proper operation).

I've opted to run the PDM task within the main loop provided by the Arduino framework (at `osPriorityNormal`), while the BLE task operates on a separate thread at `osPriorityBelowNormal`. Leveraging the [CMSIS-RTOS abstraction API](https://os.mbed.com/docs/mbed-os/v6.16/apis/thread.html) provided by Mbed enables priority configuration. Additionally, before the main loop restarts, control is yielded to the scheduler to ensure proper execution (the default RTOS tick frequency is 1kHz).

Internally, the PDM library employs a circular buffer, which is repeatedly copied into the user's [sample buffer](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/51feb5f0b0abefecbba297cffd588a23114bfa25/src/main.cpp#L22), subsequently copied into the `Serial` buffer (Arduino-Mbed's Serial API utilizes the [Async Writer](https://github.com/arduino/ArduinoCore-mbed/blob/2d27acf719a2092f161c0e521c7521fb4dd1a0b7/cores/arduino/USB/USBCDC.cpp#L43) class, ensuring that each `Serial.write` call saves the buffer dynamically into a separate memory space, mitigating concerns about timing discrepancies between microphone ADC and Serial writing, see [here](https://forum.arduino.cc/t/time-taken-for-serial-write-function-in-arduino-using-atmega2560-chip-with-baud-rate-115200/1165817/2) for more).

A [Python script](https://github.com/TIT8/BLE-sensor_PDM-microphone/tree/master/python_receiver) is employed to receive and process the samples, generating an audio file, interfacing with [***Wit.AI***](https://wit.ai/), and controlling the bedroom light as demonstrated in a [previous project](https://github.com/TIT8/shelly_esp32_button_espidf) upon detection of specific keywords. 

### Requirements

* [Arduino Nano 33 BLE Sense](https://docs.arduino.cc/hardware/nano-33-ble-sense/) or similar ([nRF52840](https://content.arduino.cc/assets/Nano_BLE_MCU-nRF52840_PS_v1.1.pdf)).
* [PlatformIO](https://platformio.org/) (easily adaptable to other environments).
* [ArduinoBLE](https://github.com/arduino-libraries/ArduinoBLE) library.
* [Arduino_HTS221](https://github.com/arduino-libraries/Arduino_HTS221) library.
* Hardware capable of running Python connected to a serial port.

## How to test the BLE task?

Utilize [nRF Connect](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile) on a smartphone, a [Python script](https://github.com/TIT8/BLE-sensor_PDM-microphone/tree/master/python_test_ble) on PC/MAC, or an [ESP32](https://github.com/TIT8/BLE_esp32) if available.

<img src="https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/3d87bad1-526b-4154-853f-053570986b97" width="200" height="400">
<img src="https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/cea82b78-370a-49f6-8f3a-3a4cce8ff1a8" width="200" height="400">



### Goals 😎

* Direct use of the [official nRF SDK](https://www.nordicsemi.com/Products/Development-software/nRF-Connect-SDK).
* Attempting to replicate functionality on ESP32 via ESP-IDF BLE library. &nbsp; [[DONE ✔️]](https://github.com/TIT8/BLE_esp32)
* Offline speech recognition via a pre-trained machine learning model using TinyML and Tensorflow. &nbsp; [[STARTED :construction_worker:]](https://github.com/TIT8/shelly_button_esp32_arduino/tree/master/speech_recognition)
