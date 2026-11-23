"""Deterministic, explainable candidate extraction for IELTS learning sources.

This module labels source passages using lexical cues only. It does not summarize,
validate educational claims, or infer semantic meaning.
"""
from __future__ import annotations

import re

TOPIC_PATTERNS = {
    "writing_task_1": r"\b(?:writing\s+)?task\s*1\b|\btask\s+one\b|رایتینگ\s*۱",
    "writing_task_2": r"\b(?:writing\s+)?task\s*2\b|\btask\s+two\b|رایتینگ\s*۲",
    "writing": r"\bwriting\b|\bessay\b|\bparagraph\b|\bintroduction\b|\bconclusion\b|رایتینگ|انشا",
    "speaking_part_1": r"\bspeaking\s+part\s*1\b|\bpart\s+one\b",
    "speaking_part_2": r"\bspeaking\s+part\s*2\b|\bcue\s+card\b|\blong\s+turn\b",
    "speaking_part_3": r"\bspeaking\s+part\s*3\b",
    "speaking": r"\bspeaking\b|\bfluency\b|\bpronunciation\b|\bspoken\b|اسپیکینگ|مکالمه",
    "reading": r"\breading\b|\bskimming\b|\bscanning\b|\bpassage\b|ریدینگ",
    "listening": r"\blistening\b|\baudio\b|\bdistractor\b|\bdictation\b|لیسنینگ",
    "vocabulary": r"\bvocabulary\b|\blexical\b|\bword\s+choice\b|لغت|واژگان",
    "grammar": r"\bgrammar\b|\btense\b|\bsentence\s+structure\b|دستور\s+زبان|گرامر",
    "pronunciation": r"\bpronunciation\b|\bstress\b|\bintonation\b|تلفظ",
    "time_management": r"\btime\s+management\b|\btime\s+limit\b|\bminutes?\b|مدیریت\s+زمان|دقیقه",
    "exam_strategy": r"\bielts\b|\bexam\b|\btest\s+strategy\b|\bband\s+[0-9]\b|آیلتس|آزمون",
}

RECOMMENDATION_CUES = re.compile(
    r"\b(?:should|must|need to|have to|try to|avoid|make sure|recommend|advise|"
    r"strategy|tip|it is better to|you can|you should)\b|"
    r"باید|بهتر است|توصیه می(?:کنم|شود)|پیشنهاد می(?:کنم|شود)|سعی کن|پرهیز کن|لازم است",
    re.IGNORECASE,
)
CLAIM_CUES = re.compile(
    r"\b(?:research shows|studies show|evidence|proven|guarantee|always|never|"
    r"improves?|increases?|decreases?|causes?|results? in|leads? to)\b|"
    r"پژوهش نشان|تحقیقات|شواهد|ثابت شده|تضمین|همیشه|هرگز|باعث می|افزایش می|بهبود می",
    re.IGNORECASE,
)
EXAMPLE_CUES = re.compile(
    r"\b(?:for example|for instance|e\.g\.|such as)\b|برای مثال|به عنوان نمونه|مثلاً",
    re.IGNORECASE,
)


def _title(text: str, limit: int = 120) -> str:
    """Return a deterministic display label, not a generated summary."""
    first = re.split(r"(?<=[.!?؟。！？])\s+|\n", text.strip(), maxsplit=1)[0]
    first = " ".join(first.split())
    if len(first) > limit:
        first = first[: limit - 1].rstrip() + "…"
    return first or "Untitled passage"


def classify_segment(text: str) -> dict:
    """Classify one segment with transparent lexical cues and exact source text."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("segment text must be non-empty text")

    normalized = text.casefold()
    topics = [
        topic
        for topic, pattern in TOPIC_PATTERNS.items()
        if re.search(pattern, normalized, re.IGNORECASE)
    ]
    if not topics:
        topics = ["unclassified"]

    if CLAIM_CUES.search(normalized):
        kind = "claim"
        review_reason = "Source assertion; evidence has not been independently checked."
    elif RECOMMENDATION_CUES.search(normalized):
        kind = "recommendation"
        review_reason = "Advice extracted from the source; suitability has not been validated."
    elif "?" in text or "؟" in text:
        kind = "question"
        review_reason = "Question or open issue; no answer is inferred."
    elif EXAMPLE_CUES.search(normalized):
        kind = "example"
        review_reason = "Example detected; its correctness and ownership are not assessed."
    else:
        kind = "note"
        review_reason = "Passage retained as a searchable note; no semantic claim is made."

    return {
        "kind": kind,
        "title": _title(text),
        "topic_tags": topics,
        "status": "needs_review",
        "review_reason": review_reason,
        "extraction_method": "deterministic-lexical-v1",
    }
