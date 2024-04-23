## Introduction

To comprehend the functionality of the PDM microphone and evaluate the quality of the captured audio, you can utilize the [pdm_serial.py](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/master/python_receiver/pdm_serial.py) script to listen for a few seconds and save the results in a `wav` file. In the repo there is an example recording named _microphone-results.wav_.

❗ Ensure that you have `scipy`, `numpy` and `pyserial` installed and configured the [required serial port](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/390e56321a8d2af8cab012b177ed7ffe3d0852b2/python_receiver/pdm_serial.py#L21) in the script. If you don't know what the port name is, try the code below in the Python console:

```python3
from serial.tools.list_ports import comports

for port in comports():
        print(port)
```

## The Recognizer Script :monocle_face:

Samples from the Arduino Nano 33 BLE Sense PDM microphone arrive at a sample rate of 16 kHz and are 16 bits per sample. The PDM code fills a buffer of 512 samples, each 16 bits. This buffer is then passed to `Serial.write()`, which writes 1024 bytes and proceeds to refill the same buffer for the next burst. Therefore, to record for the desired duration, we read 'fsamp' * 'seconds' transactions and store them in the NumPy buffer. Essentially, we read 1024 bytes each time and convert them into a NumPy array of 512 items with a size of `numpy.int16`. Hence, it's more convenient to think in terms of bytes to approximate the listening duration.

```python3
# Serial COMM
baudrate = 115200

# Preparing buffers
y = np.array([], np.int16)
z = np.array([], np.int16)

# Signal processing variables
bufsize = 512   # It's the size of the numpy array 'x'
seconds_to_reset = 200 
conversion = 32     # 32 conversion * 512 bufsize == 1 second at 16KHz of sample rate (almost)
N = seconds_to_reset * conversion * bufsize     # == [seconds] of recording (almost)
samp = False
i = 0
listening_for = 1.5   # * conversion == [second/bufsize]
trigger_volume = 17000  # If the audio samples have magnitude greater than this start listening
```

This runs in an Asyncio executor in the background. We use Asyncio StreamReader and StreamWriter as interfaces with the serial port. The try and except block will handle problems with the connection.

```python3
try:
    reader, writer = await serial_asyncio_fast.open_serial_connection(url=serial_port_ACM, baudrate=baudrate)
    print(writer.transport.get_extra_info("serial"))
except:
    print("Problem with serial connection")
    writer = None
    event.clear()
```

If a connection is established, we begin to receive data, handling any eventual timeouts.

```python3
while event.is_set() and not stop.is_set():
    
    deadline = loop.time() + 1
    try:
        async with asyncio.timeout_at(deadline):
            data = await reader.readexactly(bufsize * 2)    # In order to read 512 samples of 16 bit each, I need 1024 bytes
    except:
        break
```

Once 1024 bytes are received, we must process the data, so NumPy comes into play, transforming the data read into a buffer of 512 samples of 16 bits each. We save incoming samples in the `y` buffer; this way, we collect the history of the sampled audio.

```python3
    # Data in input is buffered as 16bit, so 1024 bytes are coming at burst
    x = np.frombuffer(data, np.int16)
    # Continuous data recording
    y = np.append(y, x, axis=0)
```

Now onto the fun part: digital signal processing. We have present data (`x`) and past data (`y`). If the volume of the present data is too high, we start sampling for a time given by the `listening_for` variable, collecting the samples in the `z` buffer. For instance, when I say "ACCENDI LUCE", usually from an audio point of view, the "C" is what goes above the volume limit, so there is a possibility to cut the starting of the keywords. This is where `y` (the history) comes into play: at the beginning, `z` will save the second before the sampling starts.

```python3
    '''
        Run to completion state machine, non blocking
    '''
    if x.max(0) >= trigger_volume and not samp:
        # Too loud, start listening for <listening_for>
        samp = True

    if samp == True and i <= listening_for * conversion:
        # Collect also the second before the activation
        if i == 0 and y.size > conversion * bufsize: z = np.append(z, y[-(conversion + 1) * bufsize:-bufsize], axis=0)
        z = np.append(z, x, axis=0)
        i += 1

    # Use >= to be sure to enter in this state
    if z.size >= (bufsize * (listening_for + 1) * conversion) and i >= listening_for * conversion:
        # Send to speech recognizer thread and reset 
        audio_queue.put(z)
        z = np.array([], np.int16)
        samp = False
        i = 0
    elif i >= listening_for * conversion:
        # Restart listening without sending (this happen when mic is connected, it return high value, but meaningless)
        z = np.array([], np.int16)
        samp = False
        i = 0

    if y.size >= N and not samp:
        # Keep the last half of the background recording
        y = np.delete(y, np.s_[math.ceil(-y.size/2)-1::-1], 0)
```

So when enough data is collected, it is sent via a [Queue](https://docs.python.org/3/library/queue.html) to the recognizer thread that is waiting for it, resetting all the variables to become ready to start new sampling. When `y` becomes large enough, we cut the first part and start writing on the last one, swapping the two first.

Subsequently, we transmit the data to Wit.Ai, and the received string is utilized to search for matching keywords, determining the action to be taken with the bedroom light. The light is controlled through a Shelly Plus 1 relay connected to an MQTT broker on a Raspberry Pi 4, where the recognizer script also runs (via a scheduled worker in systemctl). This is why _paho_ will connect to _localhost_.

```python3
while True:
        audio_sample = audio_queue.get()
        if audio_sample is None: break

        audio = sr.AudioData(audio_sample, fsamp, 2)  # retrieve the next audio processing job from the main thread
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
```

❗ The script is capable of searching for an Arduino device attached to the serial port and will automatically establish a connection to it, managing any eventual disconnection on its own. <ins>You won't need to make any changes</ins>.   
Obviously, there are multiple methods to detect serial ports. The most straightforward one is outlined in [this pull request](https://github.com/pyserial/pyserial/pull/658/files). However, here I also aim to detect whether the port is open, raising a serial.SerialException otherwise.

```python3
'''
    Find serial port where PDM MIC is attached
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
```

In the main loop, signals like `CTRL`+`C` or SIGTERM (via `sudo systemctl stop <name of the service>`) are handled to stop the script. Otherwise, it will restart gracefully, stopping coroutine and loop, and creating a new one. It is important for the `subprocess` routine in Python to disconnect the serial port before reusing it; otherwise, Linux can complain about multiple processes hogging the serial port, and it will attempt to change the name.

```python3
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
```

```python3
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
```

## Curiosity

If you use the script on Windows, using `read(1024)` or `readexactly(1024)` methods of the reader coming from `open_serial_connection` won't make any difference because the PySerial Asyncio library on Windows is based on [busy polling](https://github.com/home-assistant-libs/pyserial-asyncio-fast/blob/c3153083a5fb734f4361215ce404a2421b2664b7/serial_asyncio_fast/__init__.py#L324) (the loop calls the OS every 5ms to read samples until 1024 bytes, which is the [default limit](https://github.com/home-assistant-libs/pyserial-asyncio-fast/blob/c3153083a5fb734f4361215ce404a2421b2664b7/serial_asyncio_fast/__init__.py#L70) of the library).

While on Linux, it is important. Asyncio will return immediately when looking at the file descriptor, and it is not guaranteed with the `read()` method to obtain enough samples. <ins> Yes, `read(1024)` in this way can provide low latency, but then the signal processing part of the code is prone to bugs </ins> (you can fix it using the `x.size` variable instead of `bufsize`, but still, it isn't the best solution).

## Required Packages

Import the necessary packages into your Python environment. The packages used are:

* [Pyserial](https://github.com/pyserial/pyserial) master branch (`pip install git+https://github.com/pyserial/pyserial`)
* [Pyserial asyncio fast](https://github.com/home-assistant-libs/pyserial-asyncio-fast) because it is more up-to-date (`pip install git+https://github.com/home-assistant-libs/pyserial-asyncio-fast`)
* Numpy
* [Speech Recognition](https://pypi.org/project/SpeechRecognition/)
* [Paho MQTT](https://pypi.org/project/paho-mqtt/)

## References

* [Excellent example of using Pyserial with AsyncIO](https://tinkering.xyz/async-serial/) :yum:
* [How to schedule a Python script on Linux](https://medium.com/codex/setup-a-python-script-as-a-service-through-systemctl-systemd-f0cc55a42267)
* [How to list the serial ports using Python](https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python)
* [Loop signal handlers](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.add_signal_handler)
* [My previous project](https://github.com/TIT8/shelly_button_esp32_arduino/tree/master/speech_recognition)
