#include <Arduino.h>
#include <PDM.h>
#include <Arduino_HTS221.h>
#include <ArduinoBLE.h>
#include <mbed.h>

using namespace mbed;
using namespace rtos;
using namespace std::chrono_literals;



/*
PDM config section
*/

// default number of output channels
static const char channels = 1;
// default PCM output frequency
static const int frequency = 16000;
// Buffer to read samples into, each sample is 16-bits
short sampleBuffer[512];
// Number of audio samples read
volatile int samplesRead;
// Define PDM task callback
void onPDMdata();



/*
BLE config section
*/

BLEService humService("181A"); // Enviromental Sensing Service UUID
BLEDescriptor humDescriptor("2901", "Humidity"); // Characteristic User Description UUID
// I'm using the 0x2A6F UUID for humidity sensors, but you can use your custom one 
BLEUnsignedLongCharacteristic humCharacteristic("2A6F", BLERead | BLENotify);
void updateHumidityValue();
float old_hum = 0;
long previousMillis = 0;   



/*
Mbed OS and RTOS config section
*/

void ble_loop();
// The priority must be less than PDM thread's priority
Thread ble_thread(osPriorityBelowNormal);
// LED to indicate connection with other devices
DigitalOut led(P0_13);



/*
Setup
*/

void setup() 
{
  // Start thread
  ble_thread.start(ble_loop);

  // Baudrate need to be equal to receiver's one
  Serial.begin(115200);
  while (!Serial);

  // Configure the data receive callback
  PDM.onReceive(onPDMdata);

  // Max possible gain and buffer size
  PDM.setBufferSize(1024);
  PDM.setGain(80);

  // Initialize PDM with:
  // - one channel (mono mode)
  // - a 16 kHz sample rate for the Arduino Nano 33 BLE Sense
  if (!PDM.begin(channels, frequency)) 
  {
    Serial.println("Failed to start PDM!");
    while (1);
  }

}



/*
  PDM thread (on the main one)
*/

void loop()
{
  // Wait for samples to be read
  if (samplesRead) 
  {
    // Send 512 samples of 16 bit each (total 1024 bytes)
    Serial.write((uint8_t *)sampleBuffer, sizeof(sampleBuffer));

    // Clear the read count
    samplesRead = 0;
  }

  // Give the BLE thread chance to run
  ThisThread::sleep_for(1ms);
}


/**
  Callback function to process the data from the PDM microphone.
  NOTE: This callback is executed as part of an ISR.
  Therefore using `Serial` to print messages inside this function isn't supported.
* */
void onPDMdata() 
{
  // Query the number of available bytes
  int bytesAvailable = PDM.available();

  // Read into the sample buffer
  PDM.read(sampleBuffer, bytesAvailable);

  // 16-bit, 2 bytes per sample
  samplesRead = bytesAvailable / 2;
}



/*
  BLE thread (on this thread Serial must not be touched)
*/

void ble_loop()
{
  // Initialize sensor
  if (!HTS.begin()) 
  {
    while (1);
  }

  // Start BLE radio
  if (!BLE.begin()) 
  {
    while (1);
  }

  // Name seen when discovery the Arduino board
  BLE.setLocalName("Humidity monitor");
  BLE.setAdvertisedService(humService);
  humService.addCharacteristic(humCharacteristic);
  humCharacteristic.addDescriptor(humDescriptor); 
  BLE.addService(humService);
  humCharacteristic.writeValue(old_hum);
  /* 
    Start advertising Bluetooth® Low Energy.  It will start continuously transmitting Bluetooth® Low Energy
    advertising packets and will be visible to remote Bluetooth® Low Energy central devices
    until it receives a new connection 
  */
  BLE.advertise();

  while (true)
  {
  // wait for a Bluetooth® Low Energy central
    BLEDevice central = BLE.central();

    // if a central is connected to the peripheral:
    if (central) 
    {
      led.write(1);

      // check the humidity value every 300ms (*)
      // while the central is connected:
      while (central.connected()) 
      {
        long currentMillis = millis();
        // if 300ms have passed, check the humidity value:
        if (currentMillis - previousMillis >= 300) 
        {
          previousMillis = currentMillis;
          updateHumidityValue();
        }
      }

      // when the central disconnects, turn off the LED:
      led.write(0);
    }
  }
}


// Maybe it's better to defer this via an Event Queue? (https://os.mbed.com/docs/mbed-os/v6.16/apis/eventqueue.html)
void updateHumidityValue()
{
  float humidity = HTS.readHumidity();

  // Send only when a significant change is sensed
  if (abs(old_hum - humidity) >= 1 )
  {
    // Write in Little Endian (https://github.com/arduino-libraries/ArduinoBLE/blob/98ff550988912ffbaeb1d877970e9e05f1de0599/src/BLETypedCharacteristic.h#L69)
    humCharacteristic.writeValue(humidity * 100);  
    old_hum = humidity;
  }
}



/*
  (*) it depends on the actual RTOS implementation
*/
