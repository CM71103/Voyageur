from pydantic import BaseModel
from typing import Literal


class Activity(BaseModel):
    activity: str
    location: str
    duration_minutes: int
    estimated_cost_inr: float
    notes: str


class DayPlan(BaseModel):
    day_number: int
    morning: Activity
    afternoon: Activity
    evening: Activity


class TripBrief(BaseModel):
    destination: str
    duration_days: int
    num_travelers: int
    budget_tier: Literal["budget", "mid", "luxury"]
    interests: list[str]
    pace: Literal["relaxed", "moderate", "packed"]
    dietary_needs: list[str]
    notes: str


class Itinerary(BaseModel):
    brief: TripBrief
    days: list[DayPlan]
    total_estimated_cost: float


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
