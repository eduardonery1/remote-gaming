from aiohttp import web
from collections import defaultdict
import asyncio
import json
import logging

logging.basicConfig(level=logging.DEBUG)

routes = web.RouteTableDef()
offers = {} 
answers = {}
lock = asyncio.Lock()

@routes.post("/offer")
async def offer(request):
    data = await request.json()
    peer_id = data["peer_id"]
    offer = data["offer"]
    queue = asyncio.Queue()
    ans_queue = asyncio.Queue()
    async with lock:
        offers[peer_id] = queue
        answers[peer_id] = ans_queue
    await queue.put(offer)
    logging.info(f"Offer received from {peer_id}.")
    return web.json_response({'message': 'Offer received'})

@routes.post("/answer")
async def answer(request):
    data = await request.json()
    peer_id = data["peer_id"]
    answer = data["answer"]
    if not peer_id in answers:
        queue = asyncio.Queue()
        async with lock:
            answers[peer_id] = queue
    await answers[peer_id].put(answer)
    logging.info("Answer received.")
    return web.json_response({"message": "Answer received"})

@routes.get("/offer/{peer_id}")
async def offer_messages(request):
    peer_id = request.match_info["peer_id"]
    if peer_id not in offers:
        return "Offer not found."
    async with lock:
       queue = offers[peer_id]
    msg = await queue.get()
    queue.task_done()
    return web.json_response({"offer": msg})
 
@routes.get("/answer/{peer_id}")
async def answer_messages(request):
    peer_id = request.match_info["peer_id"]
    if not peer_id in answers:
        return "Answer not found."
    async with lock:
        queue = answers[peer_id]
    msg = await queue.get()
    queue.task_done()
    return web.json_response({"answer":msg})

app = web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app, port=8080)

