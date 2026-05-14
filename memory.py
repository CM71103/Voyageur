import os
from mem0 import MemoryClient


_memory_client = None


def get_memory_client():
    global _memory_client
    if _memory_client is None:
        api_key = os.getenv("MEM0_API_KEY")
        if api_key and api_key not in ("your-mem0-api-key-here", ""):
            _memory_client = MemoryClient(api_key=api_key)
    return _memory_client


def fetch_memories(user_id: str) -> str:
    client = get_memory_client()
    if client is None:
        return ""
    try:
        results = client.get_all(user_id=user_id)
        if not results or not results.get("results"):
            return ""
        texts = []
        for r in results["results"]:
            txt = r.get("memory", "")
            if txt:
                texts.append(txt)
        return "\n".join(texts) if texts else ""
    except Exception:
        return ""


def save_memory(user_id: str, text: str):
    client = get_memory_client()
    if client is None:
        return
    try:
        client.add(text, user_id=user_id)
    except Exception:
        pass


def get_all_memories(user_id: str):
    client = get_memory_client()
    if client is None:
        return []
    try:
        results = client.get_all(user_id=user_id)
        if not results or not results.get("results"):
            return []
        return results["results"]
    except Exception:
        return []
