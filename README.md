## Humidity sensor via BLE

I'm starting to understand RSSI and advertising, services and characteristics, default and custom UUID, GAP and GATT, peripheral/server and central/client concepts of Bluetooth Low Energy via the [Arduino Nano 33 BLE Sense](https://docs.arduino.cc/hardware/nano-33-ble-sense/). 

Here I'm using the [Notify](https://community.nxp.com/t5/Wireless-Connectivity-Knowledge/Indication-and-Notification/ta-p/1129270) feature of BLE, something like pub-sub protocols (MQTT). Check the [Arduino documentation](https://docs.arduino.cc/tutorials/nano-33-ble/bluetooth/) and the what the standard says about Service/Characteristics/Descriptors for the [Environmental Sensing Service](https://www.bluetooth.com/specifications/specs/environmental-sensing-service-1-0/) 📡.

_What's better than Arduino for learning something new?_ 💪

## Speech recognition with Wit.AI

Since Arduino Nano 33 BLE sense is built on [Mbed os](https://os.mbed.com/mbed-os/) and the [nrf52840](https://infocenter.nordicsemi.com/index.jsp?topic=%2Fcom.nordic.infocenter.nrf52832.ps.v1.1%2Fpdm.html) features an analog to digital frontend from a [microphone](https://docs.arduino.cc/tutorials/nano-33-ble-sense/microphone-sensor/) through a PDM-to-PCM chain to memory via DMA transfers, I used an RTOS thread to listen in background to the microphone and send audio samples to a Python receiver where the samples are processed.

### Requirements

* [Arduino Nano 33 BLE Sense](https://docs.arduino.cc/hardware/nano-33-ble-sense/) or similar ([nRF52840](https://content.arduino.cc/assets/Nano_BLE_MCU-nRF52840_PS_v1.1.pdf)).
* [Platformio](https://platformio.org/) (easy to port to other enviroment).
* [ArduinoBLE](https://github.com/arduino-libraries/ArduinoBLE) library.
* [Arduino_HTS221](https://github.com/arduino-libraries/Arduino_HTS221) library.

## How to test?

Using [nRF Connect](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile) on the smartphone or via a [python script](https://github.com/TIT8/BLE/tree/master/python_test_ble) on PC/MAC or via an [esp32](https://github.com/TIT8/BLE_esp32) if you have one.

<img src="https://github.com/TIT8/BLE/assets/68781644/963c1eb2-d931-46c0-95f1-b056321efaee" width="200" height="400">
<img src="https://github.com/TIT8/BLE/assets/68781644/383c2047-a255-4287-9bcb-be2261b8eeb6" width="200" height="400">


### Goals 😎

*  Use directly the [official nRF SDK](https://www.nordicsemi.com/Products/Development-software/nRF-Connect-SDK).
*  Trying to do the same things on ESP32 via ESP-IDF BLE library. &nbsp; [[DONE ✔️]](https://github.com/TIT8/BLE_esp32)
