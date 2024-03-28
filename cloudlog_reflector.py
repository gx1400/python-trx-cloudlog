#!/usr/bin/env python

# cloudlog_reflector.py

# Copyright (c) 2024 Derek Rowland NZ0P

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import time
import signal
import asyncio
import json
import websockets


last_processed_times = {}
last_stored_message = {}

async def send_message(websocket, message):
    await websocket.send(message)
    print(f"Sent message: {message}")

async def receive_response(websocket):
    response = await websocket.recv()
    print(f"Received response: {response}")

async def process_message(websocket, message, min_interval, override = False):
    global last_processed_times
    global last_stored_message

    current_time = time.time()
    data = json.loads(message)
    msgtype = data.get('request', None)
    

    if msgtype == "status-update":
        radio = data.get('from')
        last_processed_time = last_processed_times.get(radio, 0)

        if current_time - last_processed_time >= min_interval or override:  
            status = data.get('status', None)

            if status is None:
                return

            radiofreq = status.get('frequency', None)
            radiomode = status.get('mode', None)

            if radiofreq is None or radiomode is None:
                return

            out = {
                "to": "cloudlog",
                "request": "radio",
                "radio": radio,
                "frequency": radiofreq,
                "mode": radiomode
            }
            outmsg = json.dumps(out)
            await send_message(websocket, outmsg)
            last_processed_times[radio] = current_time
        else:
            print(f"Ignoring message from {radio}: Too frequent")
            last_stored_message[radio] = message  # Store the last received message

async def receive_messages(websocket, min_interval):
    async for message in websocket:
        print(f"Received message from server: {message}")
        await process_message(websocket, message, min_interval)

        # Check if there's a stored message for the radio and send it if the minimum interval has passed
        radio = json.loads(message).get('from')
        if radio in last_stored_message:
            await process_message(websocket, last_stored_message.pop(radio), 
                                  min_interval, True)

def signal_handler(in_signal, frame):
    print('Keyboard interrupt! Exiting...')
    sys.exit(0)

async def main():
    signal.signal(signal.SIGINT, signal_handler)

    try:
        with open('config.json', encoding='UTF-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Config file not found!")
        return

    # Load radios from config file or raise ValueError if not found
    radios = config.get("radios")
    if radios is None:
        raise ValueError("Radios not found in config file")

    uri = config.get("websocket_uri", "ws://localhost:14290/trx-control")
    min_interval = config.get("minimum_send_interval", 0.5)

    connected = False
    while not connected:
        try:
            async with websockets.connect(uri=uri) as websocket:
                for radio in radios:
                    # Send a message to the server to start status updates for each radio
                    message_to_send = {
                        "request": "start-status-updates",
                        "to": radio
                    }
                    await send_message(websocket, json.dumps(message_to_send))
                # Receive response from the server
                await receive_response(websocket)

                # Listen for incoming messages from the server
                await receive_messages(websocket, min_interval)

            connected = True

        except ConnectionRefusedError:
            print("Connection refused. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except websockets.exceptions.ConnectionClosedError:
            print("Disconnected. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except (websockets.exceptions.WebSocketException, 
                websockets.exceptions.InvalidStatusCode, 
                TimeoutError):
            print("Failed to connect. Retrying in 5 seconds...")
            await asyncio.sleep(5)

    

if __name__ == "__main__":
    asyncio.run(main())
