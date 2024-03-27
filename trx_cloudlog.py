#!/usr/bin/env python

# trx_pyclient.py

import asyncio
import json
import websockets
import time

async def send_message(websocket, message):
    await websocket.send(message)
    print(f"Sent message: {message}")

async def receive_response(websocket):
    response = await websocket.recv()
    print(f"Received response: {response}")

async def process_message(websocket, message, min_interval):
    global last_processed_time
    current_time = time.time()

    data = json.loads(message)
    msgtype = data.get('request', None)

    if msgtype == "status-update":
        if current_time - last_processed_time >= min_interval:  # Check if enough time has elapsed since the last message
            radio = data['from']
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
            last_processed_time = current_time
        else:
            print("Ignoring message: Too frequent")

async def receive_messages(websocket, min_interval):
    async for message in websocket:
        print(f"Received message from server: {message}")
        await process_message(websocket, message, min_interval)

async def main():
    global last_processed_time
    last_processed_time = 0

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

                try:
                    # Listen for incoming messages from the server
                    await receive_messages(websocket, min_interval)
                except KeyboardInterrupt:
                    print("Exiting...")
                    raise

            connected = True
        except ConnectionRefusedError:
            print("Connection refused. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except websockets.exceptions.ConnectionClosedError:
            print("Disconnected. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except (websockets.exceptions.WebSocketException, websockets.exceptions.InvalidStatusCode):
            print("Failed to connect. Retrying in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
