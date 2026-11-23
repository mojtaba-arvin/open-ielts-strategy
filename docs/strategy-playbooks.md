# Source-grounded strategy playbooks

This module compares learner-selected cards and composes ordered drafts. It never rewrites source advice into a new factual claim or silently chooses a winner between conflicting sources.

## Comparison

`compare_recommendations(cards, relations)` shows source text side by side and includes only explicitly curated relations between the selected cards. Similar wording does not imply contradiction. The caller must supply source-linked card records with exact offsets.

## Playbook drafting

`build_playbook(cards, title=..., preferences=...)` preserves the order selected by the learner. Every step includes the card/source IDs, title, and source offsets. Cards not personally approved remain flagged for review. The output is always a draft and is never an IELTS band or educational-effectiveness claim.

Preferences are a separate data structure and are never mixed into the source record. Supported fields are a time budget, preferred skills, constraints, and practice context. The optional JSON helper stores preferences locally with restrictive best-effort permissions.

## CLI

Select card IDs explicitly and preserve their supplied order:

```bash
python scripts/knowledge_playbook.py compare --card-id card_A --card-id card_B
python scripts/knowledge_playbook.py playbook --title "My Task 2 routine" --card-id card_A --card-id card_B --preferences-json '{"time_budget_minutes":40,"preferred_skills":["writing"]}'
```

## Example

```python
draft = build_playbook(selected_cards, title="My Task 2 routine", preferences={
    "time_budget_minutes": 40,
    "preferred_skills": ["writing"],
})
```

No LLM is required. Future generative rewriting must preserve citations per step and expose every source conflict rather than blending incompatible advice.
