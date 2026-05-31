from dataclasses import dataclass
from enum import Enum


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SupportTicket:
    subject: str
    body: str


@dataclass
class TriageResult:
    urgency: Urgency
    topic: str
    reply: str
