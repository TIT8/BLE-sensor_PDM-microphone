import argparse
import asyncio
import logging
import signal
import os
import sys
from concurrent.futures.thread import ThreadPoolExecutor

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak import uuids

logger = logging.getLogger(__name__)
condition = False


# Handle CTRL+C and other stop signals
def signal_handler(sig, frame):
    global condition
    condition = True
    logger.critical('Stop signal detected!')
    if os.name == 'posix':
        logger.critical('Press <CTRL+D> or <Enter> to finish')
        # While on Windows CTRL+C is already an EOF for sys readline()


# Handler registered when event occurring
def notification_handler(characteristic: BleakGATTCharacteristic, data: bytearray):
    """Simple notification handler which prints the data received."""
    logger.info("%s notify: %.2f%%", characteristic.description, int.from_bytes(data, "little") / 100)


# Handle client request from command line
async def async_read_stdin() -> str:
    loop = asyncio.get_event_loop()
    # This is stopped whenever reach EOF from command line
    return await loop.run_in_executor(ThreadPoolExecutor(1), sys.stdin.readline)


async def main(args: argparse.Namespace):
    logger.info("starting scan...")
    global condition

    # Check what the user typed in the terminal and BLE scanning
    if args.address:
        device = await BleakScanner.find_device_by_address(
            args.address, cb=dict(use_bdaddr=args.macos_use_bdaddr)
        )
        if device is None:
            logger.error("could not find device with address '%s'", args.address)
            return
    else:
        device = await BleakScanner.find_device_by_name(
            args.name, cb=dict(use_bdaddr=args.macos_use_bdaddr)
        )
        if device is None:
            logger.error("could not find device with name '%s'", args.name)
            return
        
    logger.info("connecting to device...")

     # Handle the BLE server disconnection
    disconnected_event = asyncio.Event()

    def disconnected_callback(client):
        disconnected_event.set()
        if condition == True:
                logger.warning("BLE server disconnected!")
        else:
            if os.name == 'posix':
                logger.warning("BLE server disconnected! Please, press <CTRL+D> or <Enter> to finish")
            else:
                logger.warning("BLE server disconnected! Please, press <Enter> to finish")

    # Connection with the device requested
    async with BleakClient(device, disconnected_callback) as client:
        logger.info("Connected")

        # Convert the standard UUID to UUID used by Break API
        uuid = uuids.normalize_uuid_16(int(args.characteristic, 16))
        await client.start_notify(uuid, notification_handler)

        # Search for the desired descriptor 
        descriptor = ''
        service = client.services
        for d in service.descriptors:
            s = await client.read_gatt_descriptor(d)
            if "humidity" in str(s).lower():
                descriptor = s

        # Until stopped, give to the other coroutines chances to run,
        # since AsynIO uses a cooperative multitasking model, so the
        # while loop must block sometimes
        print('Write "read" at any time if you want to read the BLE data')
        while not condition and not disconnected_event.is_set(): 
            # Make possible to read the Characteristic even when nothing get notified
            line = await async_read_stdin()
            if "read" in str(line).lower():
                if client.is_connected:
                    hum = await client.read_gatt_char(uuid)
                    if os.name == 'nt':
                        # Bleak on Windows doesn't handle read request with the notify callback
                        logger.info("%s read: %.2f%%", str(descriptor.decode()), int.from_bytes(hum, "little") / 100)

            await asyncio.sleep(1.0) 

        # Close the connection if CTRL+C is pressed, otherwise the
        # disconnection will be handled in background
        if not disconnected_event.is_set() and condition:
            disconnected_event.set()
            if client.is_connected:
                try:
                    await client.stop_notify(uuid)
                except:
                    logger.warning("BLE server already disconnected")
        
        await disconnected_event.wait()
        
    logger.info("Disconnected successfully. Goodbye!")


if __name__ == "__main__":
    
    # Inform the user about what he has to write on the terminal
    parser = argparse.ArgumentParser()
    device_group = parser.add_mutually_exclusive_group(required=True)

    device_group.add_argument(
        "--name",
        metavar="<name>",
        help="the name of the bluetooth device to connect to",
    )
    device_group.add_argument(
        "--address",
        metavar="<address>",
        help="the address of the bluetooth device to connect to",
    )

    parser.add_argument(
        "--macos-use-bdaddr",
        action="store_true",
        help="when true use Bluetooth address instead of UUID on macOS",
    )

    parser.add_argument(
        "characteristic",
        metavar="<notify uuid>",
        help="UUID of a characteristic that supports notifications",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="sets the log level to debug",
    )

    # Parse the terminal
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )

    # Register handle for stop signals
    signal.signal(signal.SIGINT, signal_handler)

    # Run the loop and create the main task passing the user arguments
    asyncio.run(main(args))
