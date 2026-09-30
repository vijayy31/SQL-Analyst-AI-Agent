import logging
import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator

load_dotenv()

from sql_agent.sql_analyst import app as agent_graph

logger = logging.getLogger(__name__)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(api_key_header)) -> None:
    """Reject requests without the API key configured in APP_API_KEY."""
    configured_api_key = os.getenv("APP_API_KEY")
    if not configured_api_key:
        raise HTTPException(status_code=503, detail="API key is not configured.")

    if api_key is None or not secrets.compare_digest(api_key, configured_api_key):
        raise HTTPException(status_code=401, detail="Missing or invalid API key.")

app = FastAPI(
    title="SQL Agent API",
    description="HTTP API for asking questions of the configured SQL agent.",
    version="0.1.0",
    dependencies=[Depends(require_api_key)],
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, question: str) -> str:
        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty.")
        return question


class ChatResponse(BaseModel):
    answer: str
    sql_query: str
    query_results: str
    curated_question: str
    is_safe: float
    sql_type: str
    messages: list[dict[str, str]]


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Report that the API process is running without invoking the agent."""
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Run the SQL agent for a natural-language question."""
    initial_state = {
        "messages": [],
        "user_question": request.question,
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": 0.0,
        "comments": "",
        "is_correct_query": "No",
        "query_execution_result": "",
        "final_answer": "",
        "retry_count": 0,
    }

    try:
        result = agent_graph.invoke(initial_state)
    except Exception as error:
        logger.exception("SQL agent request failed")
        raise HTTPException(
            status_code=502,
            detail="The SQL agent could not complete this request.",
        ) from error

    return ChatResponse(
        answer=result.get("final_answer", ""),
        sql_query=result.get("generated_sql_query", ""),
        query_results=result.get("query_execution_result", ""),
        curated_question=result.get("curated_ques", ""),
        is_safe=result.get("is_safe", 0.0),
        sql_type=result.get("comments", ""),
        messages=[
            {"role": message.type, "content": str(message.content)}
            for message in result.get("messages", [])
        ],
    )