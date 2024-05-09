# A test client for our Arduino BLE server

## How can I use the script?

1) You have to install python and pip, then [bleak](https://github.com/hbldh/bleak?tab=readme-ov-file#installation).

2) Download the script `test.py` and enter in the folder where it's been downloaded.

3) Open a new terminal in that folder and type:

    General (I've set this <[Name of the device](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/279eed03539bcb7410006116519fe02829c34209/src/main.cpp#L148)> and <[UUID](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/279eed03539bcb7410006116519fe02829c34209/src/main.cpp#L37)>, for example):
   
   ```bash
    python test.py --name "<Name of the device>" "<UUID>"
    ```

    Windows:
    ```bash
    python test.py --name "Humidity monitor" "0x2A6F"
    ```

    Linux/MacOS [^1]
    ```bash
    python3 test.py --name "Humidity monitor" "0x2A6F"
    ```

5) If the sensor doesn't notify anything because there isn't enough variation in humidity, you can type `read` and press enter in the command line once the script has started, and it will print the last value that the BLE server has written in the Characteristic.

6) If you have a custom BLE server, you have to create your own UUID for your application. So you can [generate](https://www.uuidgenerator.net/) a custom one or choose one of the [assigned](https://www.bluetooth.com/specifications/assigned-numbers/) UUID from the standard. 

    :exclamation: I'm using the standard UUID assigned for humidity sensors (`0x2A6F`), see [here](https://github.com/TIT8/BLE/blob/20be417d86c0495ab896a8af8cc1322d0acc7b5b/src/main.cpp#L9). Make sure you set for the correct **Characteristic UUID** in the Arduino code. While the descriptor is ["Humidity"](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/279eed03539bcb7410006116519fe02829c34209/src/main.cpp#L35) with code `0x2901` (user defined as the standard says).

7) Once started the script will listen for ever and print the data coming from humidity sensor. Use `CTRL+C` to exit from the script or disconnect the Bluetooth server (Arduino here), the script will handle disconnections, but **you have to follow what the terminal says after**.

8) Make sure to have the Bluetooth enabled on your PC/MAC. And remember: this won't work in WSL (as of April 2024).

## Final results

![Screenshot (109)](https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/d4181f39-1f67-459f-bbe5-143023abd621)

[^1]: Enable bluetooth support in WSL2 if you are on Windows, see [here](https://docs.espressif.com/projects/esp-matter/en/latest/esp32c3/using_chip_tool.html#providing-access-to-bluetooth) and [here](https://github.com/dorssel/usbipd-win/wiki/WSL-support#building-your-own-usbip-enabled-wsl-2-kernel).

