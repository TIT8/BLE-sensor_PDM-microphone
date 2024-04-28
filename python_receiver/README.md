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

    # Signal processing variables
    bufsize = 512   # It's the size of the numpy array 'x'
    seconds_to_reset = 200
    conversion = 32     # 32 conversion * 512 bufsize == 1 second at 16KHz of sample rate (almost)
    N = seconds_to_reset * conversion * bufsize     # == [seconds] of recording (almost)
    samp = False
    i = 0
    n = 0
    listening_for = 1.5   # * conversion == [second/bufsize]
    trigger_volume = 17000  # If the audio samples have magnitude greater than this start listening

    # Preparing buffers
    y = np.zeros(int(N), np.int16)
    z = np.zeros(int((listening_for + 1) * conversion * bufsize), np.int16)
    t = np.zeros(int(listening_for * conversion * bufsize), np.int16)
```

We use Asyncio [`StreamReader`](https://docs.python.org/3/library/asyncio-stream.html#asyncio.StreamReader) and [`StreamWriter`](https://docs.python.org/3/library/asyncio-stream.html#asyncio.StreamWriter) as interfaces with the serial port. The try and except block will handle problems with the connection. Please read the [source code](https://github.com/home-assistant-libs/pyserial-asyncio-fast/blob/c3153083a5fb734f4361215ce404a2421b2664b7/serial_asyncio_fast/__init__.py#L560) of the `serial_asyncio_fast.open_serial_connection()` coroutine.

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
##### BE CAREFUL WITH TIMEOUTS! 
In Python, the Global Interpreter Lock (GIL) restricts execution so that only one thread can run at a time. Consequently, if we have three threads, only one can execute at any given moment. If the speech recognizer thread (referenced [below](#the-speech-recognizer-loop-run-in-another-thread)) takes too long, it can delay the release of the GIL. When the GIL is eventually released and control is returned to the asyncio loop/task, it may exceed its allotted time, triggering a coroutine timeout. This situation may lead to the serial being restarted, resulting in a loss of responsiveness for seconds.

<ins>That's why, when working in Python, I prefer using an "online API" like Wit.AI. This approach transforms a CPU-bound task like audio transcription into an IO-bound task, as it waits for responses from an external META server. During this wait period, the GIL can be released in favor of the asyncio loop, maintaining high responsiveness to user voice input.</ins> If you opt for an offline speech recognizer, consider using [multiprocessing](https://docs.python.org/3/library/multiprocessing.html) instead of multithreading, especially in Python.

```python3
while event.is_set() and not stop.is_set():
    
    deadline = loop.time() + 2        # Timeout of two seconds, enough in my tests
    try:
        async with asyncio.timeout_at(deadline):
            data = await reader.readexactly(bufsize * 2)    # In order to read 512 samples of 16 bit each, I need 1024 bytes
    except:
        print("Maybe a timeout, closing...")
        break
```

**But wait, the `pyserial` package doesn't have a `readexactly()` method!**  
Yes, this method is called on the `StreamReader` instance, which is passed to the [`create_serial_connection`](https://github.com/home-assistant-libs/pyserial-asyncio-fast/blob/c3153083a5fb734f4361215ce404a2421b2664b7/serial_asyncio_fast/__init__.py#L474) coroutine through a [`StreamReaderProtocol`](https://github.com/python/cpython/blob/692e902c742f577f9fc8ed81e60ed9dd6c994e1e/Lib/asyncio/streams.py#L180). Every time data is received, the loop will call the `data_received()` method of the `StreamReaderProtocol`, which passes data to the `StreamReader` instance. The `StreamReader` instance checks if the exact bytes are received, and if so, it returns to the awaiter (our reader).

```python3
class StreamReaderProtocol(FlowControlMixin, protocols.Protocol):
        """Helper class to adapt between Protocol and StreamReader.
        
        (This is a helper class instead of making StreamReader itself a
        Protocol subclass, because the StreamReader has other potential
        uses, and to prevent the user of the StreamReader to accidentally
        call inappropriate methods of the protocol.)
        """

        def __init__(...):
                ...

        def data_received(self, data):
                reader = self._stream_reader
                if reader is not None:
                    reader.feed_data(data)        # reader is an asyncio.StreamReader instance
```

So, looking at the Python source code, the protocol calls the `feed_data()` method, which fills the read buffer. Then, the `readexactly()` coroutine (via cooperative multitasking with other looped coroutines) will return the correct number of bytes to the waiter, if possible.

```python3
class StreamReader:

        def __init__(...):
                ...

        def feed_data(self, data):
                assert not self._eof, 'feed_data after feed_eof'
        
                if not data:
                    return
        
                self._buffer.extend(data)
                self._wakeup_waiter()
        
                if (self._transport is not None and
                        not self._paused and
                        len(self._buffer) > 2 * self._limit):
                    try:
                        self._transport.pause_reading()
                    except NotImplementedError:
                        # The transport can't be paused.
                        # We'll just have to buffer all data.
                        # Forget the transport so we don't keep trying.
                        self._transport = None
                    else:
                        self._paused = True

        async def readexactly(self, n):
                """Read exactly `n` bytes.
        
                Raise an IncompleteReadError if EOF is reached before `n` bytes can be
                read. The IncompleteReadError.partial attribute of the exception will
                contain the partial read bytes.
        
                if n is zero, return empty bytes object.
        
                Returned value is not limited with limit, configured at stream
                creation.
        
                If stream was paused, this function will automatically resume it if
                needed.
                """
                if n < 0:
                    raise ValueError('readexactly size can not be less than zero')
        
                if self._exception is not None:
                    raise self._exception
        
                if n == 0:
                    return b''
        
                while len(self._buffer) < n:
                    if self._eof:
                        incomplete = bytes(self._buffer)
                        self._buffer.clear()
                        raise exceptions.IncompleteReadError(incomplete, n)
        
                    await self._wait_for_data('readexactly')
        
                if len(self._buffer) == n:
                    data = bytes(self._buffer)
                    self._buffer.clear()
                else:
                    data = bytes(memoryview(self._buffer)[:n])
                    del self._buffer[:n]
                self._maybe_resume_transport()
                return data
```

So to learn more, check the [Python source code](https://github.com/python/cpython/blob/main/Lib/asyncio/streams.py) and [the official doc](https://docs.python.org/3/library/asyncio-protocol.html#streaming-protocols) to see how the state machine is used under the hood. &nbsp; :nerd_face:

Once 1024 bytes are received, we must process the data, so NumPy comes into play, transforming the data read into a buffer of 512 samples of 16 bits each. We save incoming samples in the `y` buffer; this way, we collect the history of the sampled audio.

```python3
        # Data in input is buffered as 16bit, so 1024 bytes are coming at burst
        x = np.frombuffer(data, np.int16)
        # Continuous data recording
        y[n * bufsize: (n+1) * bufsize] = x
```

Now onto the fun part: digital signal processing. We have present data (`x`) and past data (`y`). If the volume of the present data is too high, we start sampling for a time given by the `listening_for` variable, collecting the samples in the `z` buffer. For instance, when I say "ACCENDI LUCE", usually from an audio point of view, the "C" is what goes above the volume limit, so there is a possibility to cut the starting of the keywords. This is where `y` (the history) comes into play: at the beginning, `z` will save the second before the sampling starts. I'm using fixed size Numpy arrays, so this state machine is fast and efficient with respect to `numpy.append()` (indeed CPU utilization is decreased of 10% on both Windows and Linux going from dinamically to statically sized arrays).

```python3
        '''
            Run to completion state machine, non blocking
        '''
        if x.max(0) >= trigger_volume and not samp:
            # Too loud, start listening for <listening_for>
            samp = True
        
        if samp == True: 
            # Listen and collect data
            if i < listening_for * conversion:
                # Collect also the second before the activation
                if i == 0:
                    if n >= conversion: z[:bufsize * conversion] = y[(n - conversion) * bufsize: n * bufsize]
                    else: z[:bufsize * conversion] = np.roll(y,conversion*bufsize,0)[n * bufsize: (n+conversion) * bufsize]
                t[i * bufsize: (i+1) * bufsize] = x
                i += 1
        
            # Use >= to be sure to enter in this state
            if i >= listening_for * conversion:
                # Send to speech recognizer thread and reset 
                z[bufsize * conversion:] = t
                samp = False
                i = 0
                audio_queue.put(z)
        
        if n < conversion * seconds_to_reset - 1:
            n += 1
        else:
            n = 0
```

So when enough data is collected, it is sent via a [Queue](https://docs.python.org/3/library/queue.html) to the recognizer thread that is waiting for it, resetting all the variables to become ready to start new sampling. When `y` becomes large enough, we cut the first part and start writing on the last one, swapping the two first.

#### The speech recognizer loop run in another thread!

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
            voice = str(r.recognize_wit_new(audio, key=WIT_AI_KEY)).lower()         
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
❗ You cannot use the Python receiver as is. ❗

I've modified the source code of the [Speech Recognition library](https://github.com/Uberi/speech_recognition/pull/750) due to deprecation warning by Wit.AI. Until the pull request is accepted and integrated into a new release available via PIP, you'll need to replace the `__init__.py` file found typically when installing the library via `pip install SpeechRecognition` in the `site-packages` folder within the Python path with the [revised `__init__.py`](https://github.com/TIT8/BLE-sensor_PDM-microphone/blob/master/python_receiver/speech_recognition_update/__init__.py). If this explanation is too lengthy, you can simply substitute the `try` block with the snippet provided below. This change is also backward compatible with the previous `__init__.py` file.

```python3
        try:
            voice = str(r.recognize_wit(audio, key=WIT_AI_KEY)).lower() 
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
❗ On Windows, this receiver won't work as is because [`loop.add_signal_handler`](https://docs.python.org/3/library/asyncio-eventloop.html#unix-signals) is only compatible with Linux. Therefore, you should remove that part of the code. However, it's important to note that Windows is capable of interrupting the code even when it doesn't handle signals. **If you use WSL, this code will work as is**.

While on Linux, it is important to note that Asyncio will return immediately when observing the file descriptor, and it is not guaranteed that the `read()` method will yield enough samples. Indeed, using `read(1024)` in this manner can offer low latency, but it also exposes the signal processing section of the code to potential bugs (although you can mitigate this by utilizing the `x.size` variable instead of `bufsize`, it still may not be the optimal solution). However, with `readexactly()`, you won't notice any difference in the end. It was all conjecture 🤦‍♂️.

🦎 If you're aiming for low latency, consider shifting speech recognition from online to offline on the device, as demonstrated [here](https://github.com/TIT8/shelly_button_esp32_arduino/tree/master/speech_recognition). However, it's not necessarily a significantly better approach than the one I've described to you so far and it can be worst.

## My use case

The code runs on a Raspberry Pi 4, which is connected to the microphone. The MQTT section will connect to the broker already running on the Raspberry Pi, which is why I'm connecting to 'localhost'.

Thanks to Asyncio, the [quantum leap provided by this commit](https://github.com/TIT8/BLE-sensor_PDM-microphone/commit/4413819cae1f11877874da1769ac8dc7949ca757?diff=unified&w=1), modifying the `SpeechRecognition` library to utilize the new low-latency Wit.AI API, [`urllib3`](https://urllib3.readthedocs.io/en/stable/index.html) to send requests and Paho MQTT library 2.0, I've achieved lower latency than ever before: from the voice command ("ACCENDI LUCE" or "SPEGNERE LE LUCI") to the actions in an average of 1.4 seconds (thanks, of course, to the 1GBit Ethernet on my LAN)!

And these are the resource consumption metrics from the `top -i` Linux command:

![Screenshot (106)](https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/36042cb6-9393-4d91-8219-c88ed24495de)
![Screenshot (105)](https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/cf6c0fb1-df31-4fb9-ad09-2160c3ac28f4)

Try to listen to what Arduino Nano 3 BLE Sense produce:

```bash
ffplay -f s16le -ar 16000 microphone-results.wav
```


## Required Packages

Import the necessary packages into your Python environment. The packages used are:

* [Pyserial](https://github.com/pyserial/pyserial) master branch (`pip install git+https://github.com/pyserial/pyserial`)
* [Pyserial asyncio fast](https://github.com/home-assistant-libs/pyserial-asyncio-fast) because it is more up-to-date (`pip install git+https://github.com/home-assistant-libs/pyserial-asyncio-fast`)
* Numpy
* [Speech Recognition fork](https://github.com/TIT8/speech_recognition) master branch (`pip install git+https://github.com/TIT8/speech_recognition`)
* [Paho MQTT](https://pypi.org/project/paho-mqtt/)

## References

* [Excellent example of using Pyserial with AsyncIO](https://tinkering.xyz/async-serial/) :yum:
* [How to schedule a Python script on Linux](https://medium.com/codex/setup-a-python-script-as-a-service-through-systemctl-systemd-f0cc55a42267)
* [How to list the serial ports using Python](https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python), and [here](https://github.com/pyserial/pyserial/pull/658/files) for alternative
* [Loop signal handlers](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.add_signal_handler)
* [Wit.AI docs](https://wit.ai/docs/http/20240304/#post__speech_link)
* [My previous project](https://github.com/TIT8/shelly_button_esp32_arduino/tree/master/speech_recognition)
