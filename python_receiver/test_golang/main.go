package main

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"wav_example/wave"
)

var (
	format       = 1
	channels     = 1
	samplerate   = 16000
	bitpersample = 16
	extraparams  []byte
)

func main() {
	file_data, err := os.ReadFile("./raw_wav.bin")
	if err != nil {
		panic(err)
	}

	float_data := make([]wave.Frame, len(file_data)/8)
	reader := bytes.NewReader(file_data)
	err = binary.Read(reader, binary.LittleEndian, float_data)
	if err != nil {
		panic(err)
	}

	wfmt := wave.NewWaveFmt(format, channels, samplerate, bitpersample, extraparams)
	var buf []byte
	writer := bytes.NewBuffer(buf)
	err = wave.WriteWaveToWriter(float_data, wfmt, writer)
	if err != nil {
		panic(err)
	}

	var client = new(http.Client)
	req, err := http.NewRequest("POST", "https://api.wit.ai/dictation", writer)
	if err != nil {
		panic(err)
	}
	req.Header.Add("Authorization", "Bearer OXQODGRZS37CVZJ437WC2FYIXXJNBZRV")
	req.Header.Add("Content-Type", "audio/wav")

	resp, err := client.Do(req)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		panic(err)
	}

	json_reader := bytes.NewReader(body)
	dec := json.NewDecoder(json_reader)
	for {
		var doc map[string]any

		err := dec.Decode(&doc)
		if err == io.EOF {
			// all done
			break
		}
		if err != nil {
			log.Fatal(err)
		}

		if doc["is_final"] == true {
			fmt.Printf("%v\n", doc["text"])
		}
	}

	// What Wit.AI receive
	err = wave.WriteFrames(float_data, wfmt, "raw_wav4.wav")
	if err != nil {
		panic(err)
	}
}
