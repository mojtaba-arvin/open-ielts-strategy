"""Independent IELTS writing rubric judge; credentials/model are separate from agent runtime."""
import json
import os
import urllib.request

DIMENSIONS = (
    "task_response",
    "coherence_cohesion",
    "lexical_resource",
    "grammar_accuracy",
)


def judge(essay, task, rubric, api_key=None):
    key = api_key or os.getenv("JUDGE_API_KEY")
    if not key:
        raise RuntimeError("JUDGE_API_KEY is required for live judging")

    model = os.getenv("JUDGE_MODEL")
    if not model:
        raise RuntimeError("JUDGE_MODEL must be explicitly configured for live judging")

    prompt = {
        "task": task,
        "essay": essay,
        "rubric": rubric,
        "dimensions": list(DIMENSIONS),
        "instruction": (
            "Return JSON only: scores with integer 1..9 per dimension, overall "
            "integer 1..9, rationale with non-empty evidence-grounded text for "
            "each dimension. Not an official IELTS score."
        ),
    }
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Assess IELTS writing conservatively. Do not invent evidence."},
            {"role": "user", "content": json.dumps(prompt)},
        ],
    }).encode()
    request = urllib.request.Request(
        os.getenv("JUDGE_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        data = json.loads(response.read())

    output = json.loads(data["choices"][0]["message"]["content"])
    scores = output.get("scores")
    rationale = output.get("rationale")
    if not isinstance(scores, dict) or set(scores) != set(DIMENSIONS):
        raise ValueError("judge dimensions mismatch")
    if any(type(value) is not int or not 1 <= value <= 9 for value in scores.values()):
        raise ValueError("scores must be integers 1..9")
    if type(output.get("overall")) is not int or not 1 <= output["overall"] <= 9:
        raise ValueError("overall score must be an integer 1..9")
    if not isinstance(rationale, dict) or set(rationale) != set(DIMENSIONS):
        raise ValueError("rationale must contain exactly the four scoring dimensions")
    if any(not isinstance(value, str) or not value.strip() for value in rationale.values()):
        raise ValueError("each dimension rationale must be non-empty evidence text")

    return {
        "model": model,
        "scores": scores,
        "overall": output["overall"],
        "rationale": rationale,
    }
