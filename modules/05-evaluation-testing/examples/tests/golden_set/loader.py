import json
import pathlib
from dataclasses import dataclass, field


@dataclass
class GoldenExample:
    subject: str
    body: str
    expected_urgency: str
    notes: str = field(default="")


def load(version: str = "v1") -> list[GoldenExample]:
    path = pathlib.Path(__file__).parent / f"{version}.jsonl"
    return [
        GoldenExample(**json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
