from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.genai import errors as genai_errors

from . import models  # noqa: F401  (makes sure all tables are registered)
from .config import BASE_DIR
from .database import Base, engine
from .routers import advisor, auth, jobs, matching, resumes
from .services.llm import AIResponseError

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Resume Analyzer API",
    version="1.0.0",
    description="Upload resumes, analyze them with AI agents + RAG, get job recommendations and career advice.",
)

app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(matching.router)
app.include_router(advisor.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path"))
        messages.append(f"{field}: {err['msg']}" if field else err["msg"])
    return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})


@app.exception_handler(genai_errors.APIError)
async def gemini_handler(request: Request, exc: genai_errors.APIError):
    print("Gemini error:", exc)
    if exc.code == 429:
        return JSONResponse(status_code=429, content={
            "detail": "Gemini free-tier limit reached. Wait one minute and try again (or tomorrow if the daily limit is used up)."})
    if exc.code in (400, 401, 403):
        detail = "Gemini rejected the request. Check GEMINI_API_KEY in the .env file."
    elif exc.code == 404:
        detail = "A configured Gemini model is no longer available. Run: python -m backend.check_models"
    else:
        detail = "The AI service is temporarily unavailable. Please try again."
    return JSONResponse(status_code=502, content={"detail": detail})


@app.exception_handler(AIResponseError)
async def ai_response_handler(request: Request, exc: AIResponseError):
    return JSONResponse(status_code=502, content={"detail": "The AI returned an unexpected answer. Please try again."})


# Serves the frontend folder. Must stay LAST so it does not hide the /api routes.
app.mount("/", StaticFiles(directory=BASE_DIR / "frontend", html=True), name="frontend")