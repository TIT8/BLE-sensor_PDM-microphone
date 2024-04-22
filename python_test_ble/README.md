## How can I use the script?

1) You have to install python and pip, then [bleak](https://github.com/hbldh/bleak?tab=readme-ov-file#installation).

2) Download the script `test.py` and enter in the folder where it's been downloaded.

3) Open a new terminal in that folder and type:

    Windows:
    ```bash
    python test.py --name "Humidity monitor" "0x2A6F"
    ```

    Linux/MacOS
    ```bash
    python3 test.py --name "Humidity monitor" "0x2A6F"
    ```

4) You have to create your own UUID for your application. So you can [generate](https://www.uuidgenerator.net/) a custom one or choose one of the [assigned](https://www.bluetooth.com/specifications/assigned-numbers/) UUID from the standard.

    :exclamation: I'm using the standard UUID assigned for humidity sensors (`0x2A6F`), see [here](https://github.com/TIT8/BLE/blob/20be417d86c0495ab896a8af8cc1322d0acc7b5b/src/main.cpp#L9). Make sure you set for the correct **Characteristic UUID** in the Arduino code.

5) Once started the script will listen for ever and print the data coming from humidity sensor. Use `CTRL+C` to exit from the script or disconnect from Bluetooth the client or the server, the script will handle disconnections.

6) Make sure to have the Bluetooth enabled on your PC/MAC.

## Final results

![Screenshot (103)](https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/6a875859-1662-45c1-b1b3-2e02983dfbe4)


