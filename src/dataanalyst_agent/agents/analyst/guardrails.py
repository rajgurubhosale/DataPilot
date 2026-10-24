import json

def validate_result(fig: dict, facts: dict) -> str | None:
    """Return an error message if the result is bad, else None."""
    traces = fig.get("data", [])
    if not traces:
        return "Figure is empty (0 traces). Check data cleaning and row filtering."

    payload = json.dumps(fig)
    if len(payload) > 80_000:  # ~80 KB limit
        return f"Figure JSON is {len(payload)//1000} KB. Precompute stats with go.Box(q1=...) or aggregate before plotting."

    for t in traces:
        for key in ("x", "y"):
            v = t.get(key)
            if isinstance(v, list) and len(v) > 1000:
                return f"A trace has {len(v)} points in '{key}'. Aggregate or precompute stats first."

    if not facts.get("key_numbers"):
        return "facts['key_numbers'] is empty. Include 2-5 computed numbers."

    return None
