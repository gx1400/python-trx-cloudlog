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

import asyncio
import json
import websockets
import time

last_processed_times = {}

async def send_message(websocket, message):
    await websocket.send(message)
    print(f"Sent message: {message}")

async def receive_response(websocket):
    response = await websocket.recv()
    print(f"Received response: {response}")

async def process_message(websocket, message, min_interval):
    global last_processed_times
    current_time = time.time()

    data = json.loads(message)
    msgtype = data.get('request', None)
    radio = data.get('from')

    if msgtype == "status-update":
        last_processed_time = last_processed_times.get(radio, 0)
        if current_time - last_processed_time >= min_interval:  # Check if enough time has elapsed since the last message
            radiofreq = data['status']['frequency']
            radiomode = data['status']['mode']
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

async def receive_messages(websocket, min_interval):
    async for message in websocket:
        print(f"Received message from server: {message}")
        await process_message(websocket, message, min_interval)

async def main():
    try:
        with open('config.json') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Config file not found!")
        return

    # Load radios from config file or raise ValueError if not found
    radios = config.get("radios")
    if radios is None:
        raise ValueError("Radios not found in config file")

    uri = config.get("websocket_uri", "ws://10.10.20.136:14290/trx-control")
    min_interval = config.get("minimum_send_interval", 0.5)

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

        try:
            # Listen for incoming messages from the server
            await receive_messages(websocket, min_interval)
        except KeyboardInterrupt:
            print("Exiting...")
            raise

if __name__ == "__main__":
    asyncio.run(main())
