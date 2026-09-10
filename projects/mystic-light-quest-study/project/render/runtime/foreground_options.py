"""Explicit learning-aid options; absent legacy fields never opt in silently."""
from __future__ import annotations


def resolve_options(foreground: dict) -> dict:
    neighbors = foreground.get("neighbors", {"enabled": False})
    countdown = foreground.get("countdown", {"enabled": False, "durationMs": 3000})
    if not isinstance(neighbors, dict) or type(neighbors.get("enabled")) is not bool:
        raise ValueError("foreground.neighbors.enabled must be a boolean")
    if not isinstance(countdown, dict) or type(countdown.get("enabled")) is not bool:
        raise ValueError("foreground.countdown.enabled must be a boolean")
    duration = countdown.get("durationMs", 3000)
    if type(duration) is not int or duration != 3000:
        raise ValueError("foreground.countdown.durationMs must be 3000 (3/2/1, one second each)")
    prelude = foreground.get("preludeMode", "hidden")
    if prelude not in ("first-line", "hidden"):
        raise ValueError("foreground.preludeMode must be first-line or hidden")
    return {"neighbors": {"enabled": neighbors["enabled"]},
            "countdown": {"enabled": countdown["enabled"], "durationMs": duration},
            "preludeMode": prelude}


def configure_options(existing: dict | None, neighbors=None, countdown=None, prelude=None) -> dict:
    options = resolve_options(existing) if existing is not None else {
        "neighbors": {"enabled": True}, "countdown": {"enabled": True, "durationMs": 3000},
        "preludeMode": "first-line"}
    if neighbors is not None: options["neighbors"]["enabled"] = neighbors == "on"
    if countdown is not None: options["countdown"]["enabled"] = countdown == "on"
    if prelude is not None: options["preludeMode"] = prelude
    return options


def countdown_plan(lines: list[dict], enabled: bool, duration_ms: int) -> dict:
    """All input times have already been transformed to the output clock."""
    onset = None
    for line in lines:
        if not line.get("text", "").strip(): continue
        voiced = [part["startMs"] for part in line["parts"] if part["text"].strip()]
        onset = min(voiced) if voiced else line["startMs"]
        break
    samples = []
    if enabled and onset is not None:
        for value in (3, 2, 1):
            start, end = max(0, onset - value * 1000), min(duration_ms, onset - (value - 1) * 1000)
            if end > start: samples.append({"startMs": start, "endMs": end, "value": value})
    return {"enabled": enabled, "clock": "output", "onsetMs": onset,
            "segments": samples, "clippedAtOutputStart": bool(enabled and onset is not None and onset < 3000)}
