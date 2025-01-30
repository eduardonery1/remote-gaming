import asyncio
import pygame
import json
import logging
from aiortc import RTCPeerConnection, RTCSessionDescription
import aiohttp

logging.basicConfig(level=logging.INFO, filename="log-sender.txt")
SIGNALING_SERVER = "http://localhost:8080"

async def send_gamepad_data(channel):
    # Initialize gamepad
    pygame.init()
    pygame.joystick.init()
    num_controllers = pygame.joystick.get_count()
    if num_controllers > 0:
        for i in range(num_controllers):
            print(f"{i+1}: {pygame.joystick.Joystick(i).get_name()}")
        
        idx = None
        while True:
            try:
                idx = int(input("Select joystick number: "))
            except Exception:
                print("Select a valid number!")
            else:
                break

        joystick = pygame.joystick.Joystick(idx - 1)
    joystick.init()

    while True:
        pygame.event.pump()
        hats = [joystick.get_hat(i) for i in range(joystick.get_numhats())]
        buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
        axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
        msg = json.dumps({"buttons": buttons, "axes": axes, "hats": hats})
        print(msg)
        channel.send(msg)
        await asyncio.sleep(0.01)  # Send data at ~100Hz

async def send_signaling_message(session, endpoint, data):
    url = f"{SIGNALING_SERVER}/{endpoint}"
    async with session.post(url, json=data) as resp:
        return await resp.json()

async def get_signaling_message(session, peer_id):
    url = f"{SIGNALING_SERVER}/answer/{peer_id}"
    async with session.get(url) as resp:
        res_json = await resp.json()
        return res_json, resp.status

async def main():
    # Create WebRTC peer connection
    pc = RTCPeerConnection()
    channel = pc.createDataChannel("gamepad")

    @channel.on("open")
    def on_open():
        nonlocal channel
        print("Channel opened!")
        asyncio.create_task(send_gamepad_data(channel))

    async with aiohttp.ClientSession() as session:
        # Create and send offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        res = await send_signaling_message(session, "offer", {
            "offer": pc.localDescription.sdp
        })
        peer_id = res["peer_id"]
        print("Your code is: '"+peer_id+"'\nShare with your friend." )
        # Receive answer
        res_ans, res_status = await get_signaling_message(session, peer_id)
        if res_status == 404:
            raise Exception("Failed answer not found!.")
        await pc.setRemoteDescription(RTCSessionDescription(res_ans["answer"], "answer"))

    while True:
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    asyncio.run(main())

