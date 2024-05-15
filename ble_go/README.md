Like the python script, only different on handling disconnection from the BLE central and signals from the user.

```bash
go run main.go --name "<Name of the BLE central>" --int <16 bit UUID of the characteristic>
```

If you don't set the command line arguments (so you run only `go run main.go`), _"Humidity monitor"_ and _0x2A6F_ will be used as default.

Then follow the command line. It's been tested on Windows 11 and Linux 6.6.
