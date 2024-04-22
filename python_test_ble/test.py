import argparse
import asyncio
import logging
import signal

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


# Handler registered when event occurring
def notification_handler(characteristic: BleakGATTCharacteristic, data: bytearray):
    """Simple notification handler which prints the data received."""
    logger.info("%s: %d%%", characteristic.description, int.from_bytes(data, "little") / 100)


async def main(args: argparse.Namespace):
    logger.info("starting scan...")

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
        logger.warning("BLE server disconnected! Closing...")

    # Connection with the device requested
    async with BleakClient(device, disconnected_callback) as client:
        logger.info("Connected")

        # Convert the standard UUID to UUID used by Break API
        uuid = uuids.normalize_uuid_16(int(args.characteristic, 16))
        await client.start_notify(uuid, notification_handler)

        # Until stopped, give to the other coroutines chances to run,
        # since AsynIO uses a cooperative multitasking model
        global condition
        while not condition and not disconnected_event.is_set(): 
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