import json
import re
import time

from google import genai
from google.genai import errors, types

from ..config import CHAT_MODELS, EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)


class AIResponseError(Exception):
    """The AI returned something we could not use."""


def _generate(system: str, user: str, json_mode: bool) -> str:
    """Try each configured model in order; fall through on retired models or quota errors."""
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json" if json_mode else None,
    )
    last_error = None
    for model in CHAT_MODELS:
        for attempt in (1, 2):
            try:
                response = client.models.generate_content(model=model, contents=user, config=config)
                text = response.text
                if not text:
                    raise AIResponseError("Empty answer from AI")
                return text.strip()
            except errors.APIError as error:
                last_error = error
                print(f"[Gemini] {model} failed (code {error.code}), attempt {attempt}")
                if error.code in (429, 500, 503) and attempt == 1:
                    time.sleep(4)  # one short retry, then move to the next model
                    continue
                break
    if last_error is not None:
        raise last_error
    raise AIResponseError("No chat model configured")


def chat_json(system: str, user: str, temperature=None) -> dict:
    # temperature is accepted so the agent code needs no changes; Gemini 3 models are best left at defaults.
    text = _generate(system, user, json_mode=True)
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise AIResponseError("Invalid JSON from AI")
    if not isinstance(data, dict):
        raise AIResponseError("Unexpected AI output")
    return data


def chat_text(system: str, user: str, temperature=None) -> str:
    return _generate(system, user, json_mode=False)


def embed(text: str) -> list[float]:
    for attempt in (1, 2, 3):
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text[:8000],
                config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONS),
            )
            return list(result.embeddings[0].values)
        except errors.APIError as error:
            if error.code in (429, 500, 503) and attempt < 3:
                time.sleep(5 * attempt)
                continue
            raise
    raise AIResponseError("Embedding failed")


def embed_many(texts: list[str]) -> list[list[float]]:
    # One request per text: with gemini-embedding-2 a list of inputs may be merged into a single embedding.
    vectors = []
    for text in texts:
        vectors.append(embed(text))
        time.sleep(0.3)  # be gentle with free-tier rate limits
    return vectors