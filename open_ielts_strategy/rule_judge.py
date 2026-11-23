"""Deterministic writing diagnostics. Heuristics are not IELTS scores or examiner judgments."""
import re
from collections import Counter

DIMENSIONS = ("task_response", "coherence_cohesion", "lexical_resource", "grammar_accuracy")


def _sentences(text):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def evaluate_writing(text, *, task=None):
    """Return reproducible text diagnostics with explicitly simulated heuristic scores."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be non-empty text")
    if task is not None and (not isinstance(task, str) or not task.strip()):
        raise ValueError("task must be non-empty text when provided")

    words = re.findall(r"\b[\w’'-]+\b", text.casefold(), flags=re.UNICODE)
    if not words:
        raise ValueError("text must contain at least one word")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    sentences = _sentences(text)
    counts = Counter(words)
    unique_ratio = len(counts) / len(words)
    avg_sentence_words = len(words) / max(1, len(sentences))
    sentence_lengths = [len(re.findall(r"\b[\w’'-]+\b", s)) for s in sentences]
    varied_sentence_lengths = len(set(sentence_lengths)) > 1
    transition_markers = ("however", "therefore", "moreover", "for example", "in contrast", "finally", "firstly", "secondly")
    lower = text.casefold()
    transitions = [marker for marker in transition_markers if re.search(r"\b" + re.escape(marker) + r"\b", lower)]
    punctuation_errors = bool(re.search(r"[!?.,]{2,}|\s+[,.!?]", text))
    repeated_word_ratio = sum(n - 1 for n in counts.values()) / len(words)

    # These are transparent thresholds for regression diagnostics, not IELTS band descriptors.
    task_score = 1 + min(8, (1 if len(words) >= 80 else 0) + (2 if len(words) >= 150 else 0) + (2 if len(paragraphs) >= 3 else 0) + (1 if len(sentences) >= 5 else 0) + (2 if task and any(w in lower for w in re.findall(r"\w+", task.casefold())[:3]) else 0))
    coherence_score = 1 + min(8, (2 if len(paragraphs) >= 3 else 0) + min(3, len(transitions)) + (1 if varied_sentence_lengths else 0) + (1 if len(sentences) >= 4 else 0) + (1 if not punctuation_errors else 0))
    lexical_score = 1 + min(8, int(unique_ratio * 8) + (1 if len(words) >= 100 else 0) - (1 if repeated_word_ratio > 0.35 else 0))
    grammar_score = 1 + min(8, (2 if varied_sentence_lengths else 0) + (2 if len(sentences) >= 4 else 0) + (2 if not punctuation_errors else 0) + (1 if avg_sentence_words >= 8 else 0) + (1 if avg_sentence_words <= 30 else 0))
    raw = {
        "task_response": max(1, min(9, task_score)),
        "coherence_cohesion": max(1, min(9, coherence_score)),
        "lexical_resource": max(1, min(9, lexical_score)),
        "grammar_accuracy": max(1, min(9, grammar_score)),
    }
    evidence = {
        "word_count": len(words),
        "paragraph_count": len(paragraphs),
        "sentence_count": len(sentences),
        "unique_word_ratio": round(unique_ratio, 4),
        "average_sentence_words": round(avg_sentence_words, 2),
        "transition_markers_found": transitions,
        "possible_punctuation_format_issue": punctuation_errors,
    }
    return {
        "schema_version": 1,
        "status": "simulated-heuristic",
        "score_type": "non-validated-diagnostic-index",
        "scores": raw,
        "overall_heuristic_index": round(sum(raw.values()) / len(raw), 2),
        "evidence": evidence,
        "limitations": [
            "Not an IELTS band score, official score, examiner judgment, or validated assessment.",
            "Cannot reliably assess task fulfillment, argument quality, grammar correctness, pronunciation, or meaning.",
            "Scores are deterministic software diagnostics and must not be used to claim learner progress.",
        ],
    }
