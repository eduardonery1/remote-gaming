import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription
import aiohttp

SIGNALING_SERVER = "http://localhost:8080"
PEER_ID = "sabrina"

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

    @pc.on("datachannel")
    def on_datachannel(channel):
        print("remote datachannel received.")
        @channel.on("message")
        def on_message(message):
            print(f"Received message: {message}")

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

