"""
A static, curated set of example prompts so a frontend has something
to show a user staring at an empty chat box. The user can pick one or
ignore all of them and type their own — this endpoint doesn't gate
anything downstream.
"""

from typing import List, Optional

SUGGESTIONS = [
    {"id": "s1", "category": "creative", "text": "Write a short story about a lighthouse keeper who finds a message in a bottle"},
    {"id": "s2", "category": "creative", "text": "Brainstorm five unusual birthday gift ideas for someone who has everything"},
    {"id": "s3", "category": "coding", "text": "Explain the difference between a list and a tuple in Python, with examples"},
    {"id": "s4", "category": "coding", "text": "Review this function and suggest improvements for readability"},
    {"id": "s5", "category": "research", "text": "Summarize the main arguments for and against remote work"},
    {"id": "s6", "category": "research", "text": "Explain how vaccines train the immune system, in simple terms"},
    {"id": "s7", "category": "productivity", "text": "Help me draft a polite follow-up email after a job interview"},
    {"id": "s8", "category": "productivity", "text": "Break down 'launch a personal website' into a step-by-step plan"},
]


def get_suggestions(category: Optional[str] = None) -> List[dict]:
    if category is None:
        return SUGGESTIONS
    return [s for s in SUGGESTIONS if s["category"] == category]
