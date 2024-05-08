package main

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"slices"
	"strings"
	"syscall"
	"time"
	"wav_example/wave"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	"go.bug.st/serial"
)

var (
	format          = 1
	channels        = 1
	samplerate      = 16000
	bitpersample    = 16
	extraparams     []byte
	size            = 512
	conversion      = 32
	seconds_toreset = 210
	listening_for   = 1.5
	global          = true
)

func check(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

/*
func readexactly(n int, ser serial.Port) ([]byte, error) {
	data := make([]byte, n)
	buff := make([]byte, 0, n)
	var err error
	var i = 0

	for i < n {
		time.Sleep(33 * time.Millisecond)
		num, err := ser.Read(data)
		if err != nil {
			log.Println(err)
			buff = nil
			return buff, err
		}
		buff = append(buff, data[:num]...)
		i = i + num
	}

	return buff, err
}
*/

func wav_wit(r chan []byte, m chan string) {
	buff := make([]byte, 2*int((listening_for+1)*float64(conversion)*float64(size)))
	float_data := make([]wave.Frame, len(buff)/8)
	reader := bytes.NewReader(buff)
	var buf []byte
	writer := bytes.NewBuffer(buf)

	wfmt := wave.NewWaveFmt(format, channels, samplerate, bitpersample, extraparams)

	var client = new(http.Client)

	for {
		buff = <-r
		if buff == nil {
			break
		}

		reader.Reset(buff)
		err := binary.Read(reader, binary.LittleEndian, float_data)
		check(err)

		err = wave.WriteWaveToWriter(float_data, wfmt, writer)
		check(err)

		req, err := http.NewRequest("POST", "https://api.wit.ai/dictation", writer)
		check(err)

		req.Header.Add("Authorization", "Bearer <Wit.Ai KEY>")
		req.Header.Add("Content-Type", "audio/wav")

		resp, err := client.Do(req)
		check(err)

		body, err := io.ReadAll(resp.Body)
		check(err)

		json_reader := bytes.NewReader(body)
		dec := json.NewDecoder(json_reader)
		for {
			var doc map[string]any

			err := dec.Decode(&doc)
			if err == io.EOF {
				break
			}
			check(err)

			if doc["is_final"] == true {
				text := doc["text"].(string)
				//fmt.Printf("%s\n", text)
				if strings.Contains(strings.ToLower(text), "luc") {
					if strings.Contains(strings.ToLower(text), "accend") {
						m <- "on"
						break
					} else if strings.Contains(strings.ToLower(text), "spegn") {
						m <- "off"
						break
					}
				}
			}
		}

		err = resp.Body.Close()
		check(err)

		client.CloseIdleConnections()
		writer.Reset()
	}

	close(m)
	log.Println("Exiting wav goroutine...")
}

var messagePubHandler mqtt.MessageHandler = func(client mqtt.Client, msg mqtt.Message) {
	log.Printf("Received message: %s from topic: %s\n", msg.Payload(), msg.Topic())
}

var connectHandler mqtt.OnConnectHandler = func(client mqtt.Client) {
	log.Println("Connected to MQTT broker")
}

var connectLostHandler mqtt.ConnectionLostHandler = func(client mqtt.Client, err error) {
	log.Printf("Connect lost: %v\n", err)
}

func mqtt_func(m chan string) {
	opts := mqtt.NewClientOptions()
	opts.AddBroker("mqtt://localhost:1883")
	opts.SetClientID("Go-PDM-client")
	opts.SetDefaultPublishHandler(messagePubHandler)
	opts.OnConnect = connectHandler
	opts.OnConnectionLost = connectLostHandler
	client := mqtt.NewClient(opts)
	token := client.Connect()
	if token.Wait() && token.Error() != nil {
		log.Fatal(token.Error())
	}
	token2 := client.Subscribe("<SHELLY-ID>/status/switch:0", 2, nil)
	token2.Wait()
	log.Printf("Subscribed to topic %s\n", "<SHELLY-ID>/status/switch:0")

	for {
		s := <-m
		if s == "" {
			break
		}

		token3 := client.Publish("<SHELLY-ID>/command/switch:0", 2, false, s)
		token3.Wait()

		time.Sleep(time.Second)
	}

	client.Disconnect(250)
	log.Println("Closing MQTT client")
	time.Sleep(500 * time.Millisecond)
	log.Println("Exiting mqtt goroutine...")
}

func dsp(c, r chan []byte) {
	data := make([]byte, size*2)
	buff := make([]byte, 0, 2*int((listening_for+1)*float64(conversion)*float64(size)))
	buff2 := make([]byte, 0, 2*int((listening_for+1)*float64(conversion)*float64(size)))
	sender := bytes.NewBuffer(buff)
	reader := bytes.NewReader(data)

	x := make([]int16, size)
	y := make([]int16, 0, size*conversion*seconds_toreset)
	z := make([]int16, 0, int((listening_for+1)*float64(conversion)*float64(size)))
	i, samp := 0, false
	trigger_volume := 18000

	for {
		data := <-c
		if data == nil {
			break
		}

		reader.Reset(data)
		err := binary.Read(reader, binary.LittleEndian, x)
		check(err)

		y = append(y, x...)

		if !samp && slices.Max(x) > int16(trigger_volume) {
			samp = true
		}

		if samp && i <= int(listening_for*float64(conversion)) {
			if i == 0 && len(y) > conversion*size {
				z = append(z, y[len(y)-(conversion+1)*size:len(y)-size]...)
			}
			z = append(z, x...)
			i++
		}

		if len(z) >= int(float64(size)*(listening_for+1)*float64(conversion)) && i >= int(listening_for*float64(conversion)) {
			i = 0
			samp = false
			err := binary.Write(sender, binary.LittleEndian, z)
			check(err)
			r <- append(buff2, sender.Bytes()...)
			buff = nil
			buff2 = nil
			sender.Reset()
			z = nil
		} else if i >= int(listening_for*float64(conversion)) {
			z = nil
			buff = nil
			i = 0
			samp = false
		}

		if len(y) >= seconds_toreset*size*conversion {
			y = y[int(len(y)/2)+size:]
		}
	}

	close(r)
	log.Println("Exiting dsp goroutine...")
}

func main() {
	c := make(chan []byte, size*2*conversion*seconds_toreset)
	r := make(chan []byte)
	m := make(chan string)
	sigc := make(chan os.Signal, 1)

	signal.Notify(sigc, syscall.SIGINT, syscall.SIGTERM, syscall.SIGQUIT)
	go func() {
		<-sigc
		m <- ""
		r <- nil
		c <- nil
		global = false
	}()

	go dsp(c, r)
	go wav_wit(r, m)
	go mqtt_func(m)

	log.Println("Starting...")

	for global {
		var tty_port string
		ports, err := serial.GetPortsList()
		check(err)

		if len(ports) == 0 {
			log.Println("No serial ports found!")
			time.Sleep(5 * time.Second)
			continue
		}

		for _, port := range ports {
			//fmt.Printf("Found port: %v\n", port)
			if strings.Contains(port, "ttyACM") {
				tty_port = port
			} else if strings.Contains(port, "COM7") {
				tty_port = port
			}
		}
		if tty_port == "" {
			log.Println("Arduino board not found")
			time.Sleep(3 * time.Second)
			continue
		}

		mode := &serial.Mode{
			BaudRate: 115200,
			DataBits: 8,
			StopBits: serial.OneStopBit,
			Parity:   serial.NoParity,
		}

		log.Println(tty_port)

		ser, err := serial.Open(tty_port, mode)
		check(err)
		err = ser.ResetInputBuffer()
		check(err)

		data := make([]byte, size*2)

		for global {
			time.Sleep(32 * time.Millisecond)
			// _, err := io.ReadAtLeast(ser, data, size*2)
			_, err := ser.Read(data)
			if err != nil {
				log.Println(err)
				break
			}

			c <- data

			/*
				buff, err := readexactly(size*2, ser)
				if err != nil {
					time.Sleep(3 * time.Second)
					break
				} else if buff != nil {
					c <- buff
				}
			*/
		}
		err = ser.Close()
		log.Println("Closing serial")
		check(err)
		time.Sleep(6 * time.Second)
	}

	close(c)
	log.Println("Exiting main goroutine...")
	time.Sleep(3 * time.Second)
}
