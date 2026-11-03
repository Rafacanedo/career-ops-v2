"""
Story Bank markdown parser and query engine for Career-Ops v2.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Story:
    title: str
    tags: List[str]
    situation: str
    task: str
    action: str
    result: str
    reflection: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def parse_story_bank(text: str) -> List[Story]:
    """
    Parse a Markdown story bank into a list of Story objects.
    
    Expected format per story:
    ## Story: <Title>
    **Tags:** tag1, tag2, tag3
    
    ### Situation
    ...
    ### Task
    ...
    ### Action
    ...
    ### Result
    ...
    ### Reflection (optional)
    ...
    """
    stories: List[Story] = []
    # Split by ## Story: or ## Story -
    story_blocks = re.split(r"(?m)^##\s+Story[:\s-]+", text)

    for block in story_blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        title = lines[0].strip()

        # Parse tags: **Tags:** tag1, tag2
        tags_match = re.search(r"\*\*Tags:\*\*\s*(.+)", block, re.IGNORECASE)
        if tags_match:
            raw_tags = tags_match.group(1).split(",")
            tags = [t.strip().lower() for t in raw_tags if t.strip()]
        else:
            tags = []

        # Extract subsections
        def extract_section(section_name: str) -> str:
            pattern = rf"(?ms)^###\s+{section_name}\s*\n(.*?)(?=^###|\Z)"
            match = re.search(pattern, block, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            return ""

        situation = extract_section("Situation")
        task = extract_section("Task")
        action = extract_section("Action")
        result = extract_section("Result")
        reflection = extract_section("Reflection") or None

        if situation or task or action or result:
            stories.append(
                Story(
                    title=title,
                    tags=tags,
                    situation=situation,
                    task=task,
                    action=action,
                    result=result,
                    reflection=reflection,
                )
            )

    return stories


def load_story_bank(file_path: Path | str) -> List[Story]:
    path = Path(file_path)
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    return parse_story_bank(content)


def filter_stories(
    stories: List[Story],
    tag: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Story]:
    matched = stories
    if tag:
        tag_lower = tag.strip().lower()
        matched = [s for s in stories if tag_lower in s.tags or any(tag_lower in t for t in s.tags)]

    if limit and limit > 0:
        matched = matched[:limit]

    return matched
