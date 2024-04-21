## Walkthrough the Python code

Samples from Arduino Nano 33 BLE sense PDM microphone
arrive at 16KHz of sample rate and are 16 bit per sample.
The PDM code will fill a buffer of 512 samples, 16 bit each,
and send 8 bit (1 bytes) per single transaction. So, Serial.write() 
will write 1024 bytes and then start to refill the same buffer for the 
next burst. 
So in order to count record for the required seconds,
we read 'fsamp' * 'seconds' transactions and put them in the numpy buffer.
