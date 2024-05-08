### CPU and memory usage from `top -i` command

From my tests the average CPU load is 0.5%, 0.2% less than Python.

![Screenshot (115)](https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/7713365b-8207-445a-8d84-d8f3145f899c)
![Screenshot (114)](https://github.com/TIT8/BLE-sensor_PDM-microphone/assets/68781644/f4bb1a16-fadf-44ea-819b-e8a139c439d4)

### Difference with python

The difference lies in how the _[c|g]oroutines_ are scheduled by Go and Python runtimes, but the philosophy remains the same: sleeping to wait for enough data in the kernel buffer and then reading it to process. 

In Go, using slices directly is very fast; `append` is much faster than `numpy.append()` in Python. Therefore, in Python, I have to preallocate the numpy array and then use powerful slicing indexes. Conversely, in Go, I can append to slices directly, which is more robust when reading less than 1024 bytes at a time, while in Python, `readexactly()` from the stream is necessary before processing.
