import json
import os
import re
import httpx
from schemas import TripBrief, Itinerary, DayPlan, Activity
from prompts import (
    SYSTEM_PROMPT,
    BRIEF_EXTRACTION_PROMPT,
    ITINERARY_PROMPT,
    REFINEMENT_PROMPT,
)
from memory import fetch_memories, save_memory, get_all_memories


MODEL = os.getenv("VOYAGEUR_MODEL", "llama-3.3-70b-versatile")
API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _call_claude(system: str, messages: list, max_retries=1, json_output=False):
    api_key = os.getenv("GROQ_API_KEY")
    full_messages = [{"role": "system", "content": system}] + messages
    body = dict(
        model=MODEL,
        messages=full_messages,
        max_tokens=4096,
    )
    if json_output:
        body["response_format"] = {"type": "json_object"}

    for attempt in range(max_retries + 1):
        try:
            resp = httpx.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt < max_retries:
                continue
            raise e


def extract_brief(user_description: str) -> TripBrief:
    messages = [
        {"role": "user", "content": f"{BRIEF_EXTRACTION_PROMPT}\n\nUser description: {user_description}"}
    ]
    raw = _call_claude(SYSTEM_PROMPT, messages, json_output=True)
    data = _parse_json_safely(raw)
    if data is None:
        raw = _call_claude(SYSTEM_PROMPT, messages, json_output=True)
        data = _parse_json_safely(raw)
    if data is None:
        raise ValueError("Failed to parse trip brief after retry.")
    return TripBrief(**data)


def generate_itinerary(brief: TripBrief) -> Itinerary:
    brief_json = brief.model_dump_json(indent=2)
    prompt = f"{ITINERARY_PROMPT}\n\nTrip Brief JSON:\n{brief_json}"
    messages = [{"role": "user", "content": prompt}]
    raw = _call_claude(SYSTEM_PROMPT, messages, json_output=True)
    data = _parse_json_safely(raw)
    if data is None:
        raw = _call_claude(SYSTEM_PROMPT, messages, json_output=True)
        data = _parse_json_safely(raw)
    if data is None:
        raise ValueError("Failed to parse itinerary after retry.")
    return Itinerary(**data)


def refine_or_answer(itinerary: Itinerary, user_message: str) -> tuple[str, Itinerary | None]:
    prompt = REFINEMENT_PROMPT.format(
        current_itinerary=itinerary.model_dump_json(indent=2),
        user_message=user_message,
    )
    messages = [{"role": "user", "content": prompt}]
    raw = _call_claude(SYSTEM_PROMPT, messages)

    data = _parse_json_safely(raw)
    if data is not None:
        try:
            updated = Itinerary(**data)
            return "json", updated
        except Exception:
            pass
    return "text", raw


def _parse_json_safely(text: str | None):
    if text is None:
        return None
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        return None


def format_brief(brief: TripBrief) -> str:
    lines = [
        "=" * 60,
        "TRIP BRIEF",
        "=" * 60,
        f"Destination     : {brief.destination}",
        f"Duration        : {brief.duration_days} day(s)",
        f"Travelers       : {brief.num_travelers}",
        f"Budget          : {brief.budget_tier}",
        f"Pace            : {brief.pace}",
        f"Interests       : {', '.join(brief.interests)}",
        f"Dietary Needs   : {', '.join(brief.dietary_needs) if brief.dietary_needs else 'None'}",
    ]
    if brief.notes:
        lines.append(f"Notes           : {brief.notes}")
    lines.append("")
    return "\n".join(lines)


def format_block(block: Activity, label: str) -> str:
    cost_str = f"₹{block.estimated_cost_inr:,.0f}" if block.estimated_cost_inr else "Free"
    lines = [
        f"  [{label}]",
        f"    Activity   : {block.activity}",
        f"    Location   : {block.location}",
        f"    Duration   : {block.duration_minutes} min",
        f"    Cost       : {cost_str}",
    ]
    if block.notes:
        lines.append(f"    Notes      : {block.notes}")
    return "\n".join(lines)


def format_day(day: DayPlan) -> str:
    lines = [
        f"  DAY {day.day_number}",
        "-" * 56,
    ]
    lines.append(format_block(day.morning, "Morning"))
    lines.append("")
    lines.append(format_block(day.afternoon, "Afternoon"))
    lines.append("")
    lines.append(format_block(day.evening, "Evening"))
    lines.append("")
    return "\n".join(lines)


def format_itinerary(it: Itinerary) -> str:
    lines = [
        "=" * 60,
        "ITINERARY",
        "=" * 60,
    ]
    for day in it.days:
        lines.append(format_day(day))
    total = f"₹{it.total_estimated_cost:,.0f}" if it.total_estimated_cost else "Not calculated"
    lines.append(f"  TOTAL ESTIMATED COST: {total}")
    lines.append("")
    return "\n".join(lines)


def build_memory_context(user_id: str) -> str:
    memories = fetch_memories(user_id)
    if memories:
        return f"The user has the following known preferences from past conversations:\n{memories}\n\nAcknowledge these and ask if they still apply."
    return ""


def extract_preferences_from_history(history: list) -> list[str]:
    preferences = []
    for msg in history:
        content = msg.get("content", "")
        lower = content.lower()

        diet_keywords = ["vegetarian", "vegan", "gluten", "dairy", "allerg", "halal", "kosher", "veggie", "no meat"]
        pace_keywords = ["relaxed", "slow", "leisurely", "packed", "fast", "busy", "moderate"]
        budget_keywords = ["budget", "cheap", "affordable", "luxury", "expensive", "mid-range", "splurge"]
        dislike_keywords = ["don't like", "hate", "dislike", "not interested", "temple", "boring", "skip", "remove"]
        visited_keywords = ["been to", "visited", "already been", "went to"]

        if any(kw in lower for kw in diet_keywords):
            preferences.append(f"Dietary: {content[:200]}")
        if any(kw in lower for kw in pace_keywords):
            preferences.append(f"Pace: {content[:200]}")
        if any(kw in lower for kw in budget_keywords):
            preferences.append(f"Budget: {content[:200]}")
        if any(kw in lower for kw in dislike_keywords):
            preferences.append(f"Disliked: {content[:200]}")
        if any(kw in lower for kw in visited_keywords):
            preferences.append(f"Visited: {content[:200]}")

    return preferences


def save_session_preferences(user_id: str, history: list):
    prefs = extract_preferences_from_history(history)
    if not prefs:
        save_memory(user_id, "User had a conversation but no strong preferences were detected.")
        return
    for pref in prefs:
        save_memory(user_id, pref)


def debug_memories(user_id: str) -> str:
    items = get_all_memories(user_id)
    if not items:
        return "No memories stored yet."
    lines = ["--- Stored Memories ---"]
    for i, item in enumerate(items, 1):
        txt = item.get("memory", "")
        lines.append(f"{i}. {txt}")
    return "\n".join(lines)
