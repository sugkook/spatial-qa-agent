"""
FastAPI 接口 —— 将 Agent 暴露为 HTTP API

启动：uvicorn server:app --reload --port 8080
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

from agent import agent

app = FastAPI(title="空间智能问答Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class QueryRequest(BaseModel):
    question: str


@app.post("/ask")
async def ask(req: QueryRequest):
    """同步问答接口"""
    try:
        result = agent.invoke({"user_input": req.question, "error": ""})
        return {
            "question": req.question,
            "intent": result.get("intent", ""),
            "tool_name": result.get("tool_name", ""),
            "tool_args": result.get("tool_args", {}),
            "tool_result": result.get("tool_result", {}),
            "answer": result["final_response"],
        }
    except Exception as e:
        return {"question": req.question, "error": str(e), "answer": f"出错了: {e}"}


@app.post("/ask/stream")
async def ask_stream(req: QueryRequest):
    """流式问答接口（SSE）"""
    async def generate():
        try:
            result = agent.invoke({"user_input": req.question, "error": ""})
            answer = result.get("final_response", "")
            for char in answer:
                yield f"data: {json.dumps({'char': char})}\n\n"
                await asyncio.sleep(0.02)
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
