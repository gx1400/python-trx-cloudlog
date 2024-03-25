

import asyncio
import websockets
import json

async def send_message(websocket, message):
    await websocket.send(message)
    print(f"Sent message: {message}")

async def receive_response(websocket):
    response = await websocket.recv()
    print(f"Received response: {response}")

async def receive_messages(websocket):
    async for message in websocket:
        print(f"Received message from server: {message}")

async def keep_alive(websocket, delay):
    while True:
        await asyncio.sleep(delay)  # Send a keep-alive message every 'delay' seconds
        msg = '{"request":"ping","to":"ping"}'
        await send_message(websocket, msg)

async def main():
    try:
        with open('config.json') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Config file not found!")
        return
    
    uri = config.get("websocket_uri", "ws://localhost:8765")
    delay = config.get("keepalive_timer_delay", 5)
    
    async with websockets.connect(uri) as websocket:
        # Send a message to the server
        message_to_send = '{"request":"start-status-updates","to":"ft-817"}'
        await send_message(websocket, message_to_send)
        # Receive response from the server
        await receive_response(websocket)

        # Send a message to the server
        message_to_send = '{"to":"keepalive","request":"listen"}'
        await send_message(websocket, message_to_send)
        # Receive response from the server
        await receive_response(websocket)
        
        # Start the keep-alive task
        keep_alive_task = asyncio.create_task(keep_alive(websocket, delay))
        
        try:
            # Listen for incoming messages from the server
            await receive_messages(websocket)
        except KeyboardInterrupt:
            print("Exiting...")
            keep_alive_task.cancel()
            raise

if __name__ == "__main__":
    asyncio.run(main())
