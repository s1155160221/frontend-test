from fastapi import Request, APIRouter, HTTPException, Body, Depends

from app.utils.sse_broadcaster import SSEBroadcaster
from app.services.chat.chat_service import ChatService


router = APIRouter()
chat_service = ChatService()

@router.post("/answer")
def get_answer(payload: dict = Body(...)):
    return chat_service.answer(payload=payload)

@router.get("/history")
def get_history():
    return chat_service.history_get()

@router.delete("/history")
def delete_history():
    return chat_service.history_clear()

@router.post("/stream")
async def get_answer_stream(request: Request, payload: dict = Body(...)):
    base_event = {
        "id": payload.get("id"),
        "sessionId": payload.get("sessionId"),
        "clientId": payload.get("clientId"),
    }

    broadcaster = SSEBroadcaster(request, base_event=base_event)

    async def producer(publish):
        # Initial meta event
        if not await publish("meta", {"message": "Chat request accepted"}, status="Processing"):
            return
        # Main streaming logic delegated to service
        await chat_service.stream_answer(payload, publish)

    return broadcaster.run(producer)