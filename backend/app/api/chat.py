from fastapi import APIRouter, HTTPException, Body, Depends
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