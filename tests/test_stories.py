import pytest
from career_ops.stories.parser import parse_story_bank, filter_stories, Story

SAMPLE_STORY_MARKDOWN = """# Behavioral Story Bank

## Story: Event Bus Outage Recovery
**Tags:** distributed-systems, kafka, incident-response, reliability

### Situation
A critical payment ingestion event bus experienced a consumer group lag spike during Black Friday peak.

### Task
Restore throughput, prevent duplicate payments, and stabilize consumer offset tracking.

### Action
Rebalanced partitions, tuned buffer batch sizes, and rolled out a hotfix to unblock dead-letter queue processing.

### Result
Zero lost transactions, lag decreased to zero in 8 minutes, system sustained 45k ops/sec.

### Reflection
Automated circuit breakers are essential for consumer retries.

## Story: Cross-Functional Design System Migration
**Tags:** leadership, frontend, design-system, mentorship

### Situation
Three product squads were duplicating UI components with inconsistent accessibility standards.

### Task
Unify design tokens and lead the core component library migration.

### Action
Conducted bi-weekly architectural alignment sessions and created migration codemods.

### Result
Reduced bundle size by 35% and increased accessibility compliance to 98%.
"""


def test_parse_story_bank():
    stories = parse_story_bank(SAMPLE_STORY_MARKDOWN)
    assert len(stories) == 2
    
    s1 = stories[0]
    assert s1.title == "Event Bus Outage Recovery"
    assert "distributed-systems" in s1.tags
    assert "kafka" in s1.tags
    assert "Black Friday" in s1.situation
    assert "Zero lost transactions" in s1.result
    assert s1.reflection is not None

    s2 = stories[1]
    assert s2.title == "Cross-Functional Design System Migration"
    assert "leadership" in s2.tags
    assert s2.reflection is None


def test_filter_stories_by_tag():
    stories = parse_story_bank(SAMPLE_STORY_MARKDOWN)
    filtered = filter_stories(stories, tag="kafka")
    assert len(filtered) == 1
    assert filtered[0].title == "Event Bus Outage Recovery"

    filtered_leadership = filter_stories(stories, tag="leadership")
    assert len(filtered_leadership) == 1
    assert filtered_leadership[0].title == "Cross-Functional Design System Migration"

    filtered_none = filter_stories(stories, tag="nonexistent")
    assert len(filtered_none) == 0


def test_filter_stories_with_limit():
    stories = parse_story_bank(SAMPLE_STORY_MARKDOWN)
    filtered = filter_stories(stories, limit=1)
    assert len(filtered) == 1
