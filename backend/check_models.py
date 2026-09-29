from .config import CHAT_MODELS, EMBEDDING_MODEL
from .services.llm import client, embed


def main() -> None:
    print("Chat models (in the order they are tried):")
    for model in CHAT_MODELS:
        try:
            reply = client.models.generate_content(model=model, contents="Reply with the single word: OK")
            print(f"  OK    {model} -> {(reply.text or '').strip()[:20]}")
        except Exception as error:
            print(f"  FAIL  {model} -> {str(error)[:150]}")

    print("\nEmbedding model:")
    try:
        print(f"  OK    {EMBEDDING_MODEL} ({len(embed('hello world'))} dimensions)")
    except Exception as error:
        print(f"  FAIL  {EMBEDDING_MODEL} -> {str(error)[:150]}")

    print("\nModels your key can currently use:")
    try:
        for model in client.models.list():
            actions = getattr(model, "supported_actions", None) or []
            if "gemini" in model.name and ("generateContent" in actions or "embedContent" in actions):
                print(f"  {model.name.replace('models/', '')}  ({', '.join(actions)})")
    except Exception as error:
        print("  Could not list models:", str(error)[:150])


if __name__ == "__main__":
    main()