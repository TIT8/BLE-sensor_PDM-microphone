package main

import (
	"bufio"
	"bytes"
	"encoding/binary"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"runtime"
	"strings"
	"syscall"
	"time"

	"tinygo.org/x/bluetooth"
)

var (
	adapter          = bluetooth.DefaultAdapter
	flaguuid         int
	flagname         string
	condition        = true
	operating_system = runtime.GOOS
)

func must(action string, err error) {
	if err != nil {
		panic("failed to " + action + ": " + err.Error())
	}
}

func callback(buf []byte) {
	reader := bytes.NewReader(buf)
	var data uint32
	err := binary.Read(reader, binary.LittleEndian, &data)
	must("binary reading", err)
	fmt.Println("Humidity: ", float64(data)/100, "%")
}

func read_char(char []bluetooth.DeviceCharacteristic, c chan os.Signal) {
	scanner := bufio.NewScanner(os.Stdin)
	fmt.Println("Type \"read\" when you want if you want to read")
	for scanner.Scan() {
		if strings.Contains(strings.ToLower(scanner.Text()), "read") {
			data := make([]byte, 4)
			i, err := char[0].Read(data)
			if err != nil {
				fmt.Println("Device disconnected")
				c <- syscall.SIGINT
				break
			}
			if i > 0 {
				if operating_system == "windows" {
					callback(data)
				}
			}
		}
	}
	must("scan input", scanner.Err())
	fmt.Println("Closing command line...")
}

func connection_handler(done chan bool, f chan bluetooth.Device, c chan os.Signal) {
	d := <-f
	uuid := bluetooth.New16BitUUID(0x181A)
	u := []bluetooth.UUID{uuid}
	services, err := d.DiscoverServices(u)
	must("discover service", err)

	uuid = bluetooth.New16BitUUID(uint16(flaguuid))
	u = []bluetooth.UUID{uuid}
	char, err := services[0].DiscoverCharacteristics(u)
	must("discover characteristic", err)

	if len(char) > 0 {
		fmt.Println("Service and characteristic found!\nPress CTRL+C to exit")
		must("enabling notification", char[0].EnableNotifications(callback))
		go read_char(char, c)
	} else {
		fmt.Println("Zero characteristic found with that UUID")
		c <- syscall.SIGINT
	}

	<-done
}

func disconnect_handler(device bluetooth.Device, connected bool) {
	if !connected {
		fmt.Println("Disconnection successfull")
	} else {
		fmt.Println("Connection successfull")
	}
}

func scanner(ch chan bluetooth.ScanResult, c chan os.Signal) {
	must("enable BLE stack", adapter.Enable())

	flag.StringVar(&flagname, "name", "Humidity monitor", "You have to insert the name of the BLE central, otherwise \"Humidity monitor\" will be used as default")
	flag.IntVar(&flaguuid, "int", 0x2A6F, "Insert the UUID of the Characteristic as 16 bit integer")
	flag.Parse()

	println("Scanning...")

	start := time.Now()
	err := adapter.Scan(func(adapter *bluetooth.Adapter, device bluetooth.ScanResult) {
		if device.LocalName() == flagname {
			println("Found device:", device.Address.String(), device.RSSI, device.LocalName())
			must("stop scan", adapter.StopScan())
			ch <- device
		} else if time.Since(start)-time.Duration(start.Nanosecond()) > 10*time.Second && condition {
			must("stop scan", adapter.StopScan())
			condition = false
			fmt.Println("Device not found")
			close(ch)
			c <- syscall.SIGINT
		}
	})
	must("start scan", err)
}

func main() {
	fmt.Println(operating_system)
	c := make(chan os.Signal, 1)
	f := make(chan bluetooth.Device)
	ch := make(chan bluetooth.ScanResult)
	done := make(chan bool)

	signal.Notify(c, syscall.SIGTERM, syscall.SIGINT)
	go func() {
		<-c
		fmt.Println("Stop signal detected, closing...")
		time.Sleep(1 * time.Second)
		done <- true
	}()

	go connection_handler(done, f, c)
	go scanner(ch, c)

	var d bluetooth.Device
	var err error
	result, ok := <-ch
	if ok {
		adapter.SetConnectHandler(disconnect_handler)
		d, err = adapter.Connect(result.Address, bluetooth.ConnectionParams{})
		must("connect to device", err)
		println("Connected to ", result.LocalName())
		f <- d
	}

	<-done
	time.Sleep(1 * time.Second)
	if condition {
		must("disconnection", d.Disconnect())
		time.Sleep(5 * time.Second)
		fmt.Println("BLE disconnected")
	}
}
