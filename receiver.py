import asyncio
import aiohttp
import vgamepad as vg
import logging
from abc import ABC, abstractmethod
from pydantic import BaseModel, ValidationError
from typing import List, Dict
from aiortc import RTCPeerConnection, RTCSessionDescription

#logging.basicConfig(level=logging.INFO)
SIGNALING_SERVER = "http://localhost:8080"
PEER_ID = "sabrina"

class ControllerState(BaseModel, ABC):
    axes: List[float]
    buttons: List[float]
    hats: List[List[int]]
    mapping: List[str]

    @abstractmethod
    def get_buttons():
        raise NotImplementedError


class XBOXControllerState(ControllerState):
    def get_buttons():
        pass


class DSControllerState(ControllerState):
    mapping: List[str] = ["Y", "B", "A", "X"] * 3

    def get_buttons(self):
        active = []
        for i, btn in enumerate(self.buttons):
            if btn:
                active.append(self.mapping[i])
        return active
        

class XBOXControllerEmulator:
    def __init__(self):
        self.gamepad = vg.VX360Gamepad()
        self.btn_states = {}
        self.mapping = {"A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
                        "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
                        "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
                        "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y}
        self.lock = asyncio.Lock()
    
    async def _release(self, code: str):
        await asyncio.sleep(.05)
        async with self.lock:
            btn = self.mapping.get(code)
            self.gamepad.release_button(button=btn)
            self.gamepad.update()
            self.btn_states.pop(code)
        logging.info(f"Released button {code}")
        print(f"Released button {code}")

    async def _press(self, code: str):
        btn = self.mapping.get(code)
        async with self.lock:
            if code in self.btn_states and not self.btn_states[code].cancelled():
                self.btn_states[code].cancel()
            else:
                self.gamepad.press_button(button=btn)
                self.gamepad.update()
                logging.info(f"Pressed btn {code}")
                print(f"Pressed btn {code}")
            self.btn_states[code] = asyncio.create_task(self._release(code))

    def update(self, state: ControllerState):
        tasks = [asyncio.create_task(self._press(btn)) for btn in state.get_buttons()]
        asyncio.gather(*tasks)


async def send_signaling_message(session, endpoint, data):
    url = f"{SIGNALING_SERVER}/{endpoint}"
    async with session.post(url, json=data) as resp:
        return await resp.json()


async def get_signaling_message(session, peer_id):
    url = f"{SIGNALING_SERVER}/offer/{peer_id}"
    async with session.get(url) as resp:
        return await resp.json()


async def main():
    pc = RTCPeerConnection()
    gamepad = XBOXControllerEmulator()

    @pc.on("datachannel")
    def on_datachannel(channel):
        logging.info("remote datachannel received.")

        @channel.on("message")
        def on_message(message):
            logging.debug(f"Received message: {message}")
            try:
                state = XBOXControllerState.model_validate_json(message)
            except ValidationError:
                state = DSControllerState.model_validate_json(message)
            except Exception as e:
                raise e

            gamepad.update(state)

    async with aiohttp.ClientSession() as session:
        # Wait for offer
        offer = await get_signaling_message(session, PEER_ID)
        await pc.setRemoteDescription(RTCSessionDescription(offer["offer"], "offer"))
        print("offer received.")

        # Create and send answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await send_signaling_message(session, "answer", {
            "peer_id": PEER_ID,
            "answer": pc.localDescription.sdp
        })
        print("answer sent.")
        
    print("Current signaling state:", pc.signalingState, "senders:", pc.getSenders())
    print("Waiting events...")
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

