from fastapi import APIRouter

router = APIRouter()


@router.get("/hi-llm")
async def hello():
    return {"message": "Hello LLM World"}


@router.get("/llm")
async def prompt_llm(url: str):
    pass