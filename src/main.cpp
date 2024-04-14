#include <Arduino.h>
#include <PDM.h>

// default number of output channels
static const char channels = 1;

// default PCM output frequency
static const int frequency = 16000;

// Buffer to read samples into, each sample is 16-bits
short sampleBuffer[512];

// Number of audio samples read
volatile int samplesRead;

void onPDMdata();


void setup() {
  Serial.begin(115200);

  while (!Serial);

  // Configure the data receive callback
  PDM.onReceive(onPDMdata);
  
  // Max possible gain and buffer size
  PDM.setGain(80);
  PDM.setBufferSize(1024);

  // Initialize PDM with:
  // - one channel (mono mode)
  // - a 16 kHz sample rate for the Arduino Nano 33 BLE Sense
  if (!PDM.begin(channels, frequency)) {
    Serial.println("Failed to start PDM!");
    while (1);
  }
}


void loop() {
  // Wait for samples to be read
  if (samplesRead) {

    // Print samples to the serial monitor or plotter
    Serial.write((uint8_t *)sampleBuffer, sizeof(sampleBuffer));

    // Clear the read count
    samplesRead = 0;
  }
}

/**
  Callback function to process the data from the PDM microphone.
  NOTE: This callback is executed as part of an ISR.
  Therefore using `Serial` to print messages inside this function isn't supported.
* */
void onPDMdata() {
  // Query the number of available bytes
  int bytesAvailable = PDM.available();

  // Read into the sample buffer
  PDM.read(sampleBuffer, bytesAvailable);

  // 16-bit, 2 bytes per sample
  samplesRead = bytesAvailable / 2;
}