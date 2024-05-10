### CPU and memory usage from `top -i` command

From my tests:

- the average CPU load is 0.5%, 0.2% less than Python
- the memory usage is between 1.4% and 1.6%
- the max CPU usage is 1.3%
- the min is 0%.


![Screenshot (115)](https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/7713365b-8207-445a-8d84-d8f3145f899c)
![Screenshot (114)](https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/f4bb1a16-fadf-44ea-819b-e8a139c439d4)

### Difference with python

The difference lies in how the _[c|g]oroutines_ are scheduled by Go and Python runtimes, but the philosophy remains the same: sleeping to wait for enough data in the kernel buffer and then reading it to process (also the Go serial libray block on [`select()`](https://github.com/bugst/go-serial/blob/0925f99089e0b2f8324e7de73fd40fbfd5ddd255/serial_unix.go#L81)). [^1]

- <ins>In Go, using slices directly is very fast</ins>; `append` is much faster than `numpy.append()` in Python. Therefore, in Python, I have to preallocate the numpy array and then use powerful slicing indexes. Conversely, in Go, I can append to slices directly, which is more robust when reading less than 1024 bytes at a time, while in Python, `readexactly()` from the stream is necessary before processing.

- Much easier to make the code working on multiple OS in Go.

[^1]: Why wait is a simple question, but the [answer](https://github.com/0xAX/linux-insides/blob/master/SUMMARY.md) is long. Good reading.
