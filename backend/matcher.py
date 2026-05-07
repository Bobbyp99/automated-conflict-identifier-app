"""
matcher.py — Token-based conflict scoring engine.

Compares a disclosed financial interest (entity name) against a vote subject
and returns a 0-100 score + likelihood tier.
"""

import re
from typing import List, Tuple


STOPWORDS = {
    "the","a","an","and","or","of","in","for","to","at","by","on","with",
    "inc","llc","corp","co","ltd","dba","aka","county","city","state",
    "board","supervisors","item","consent","calendar","regular","closed",
    "session","agenda","approval","discussion","report","update","review",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", (text or "").lower())).strip()


def _tokenize(text: str) -> List[str]:
    return [t for t in _normalize(text).split() if len(t) > 2 and t not in STOPWORDS]


def compute_score(entity: str, subject: str) -> float:
    """F1-style token overlap score in [0, 1]."""
    e_tokens = _tokenize(entity)
    s_tokens = _tokenize(subject)
    if not e_tokens or not s_tokens:
        return 0.0

    s_set = set(s_tokens)
    overlap = 0.0
    for t in e_tokens:
        if t in s_set:
            overlap += 1.0
        else:
            for s in s_set:
                if len(s) > 3 and len(t) > 3 and (s in t or t in s):
                    overlap += 0.6
                    break

    p = overlap / len(e_tokens)
    r = overlap / len(s_tokens)
    if p + r == 0:
        return 0.0
    return (2 * p * r) / (p + r)


def likelihood(score: float) -> str:
    if score >= 0.35:
        return "High"
    if score >= 0.12:
        return "Medium"
    return "Low"


def run_match(interests, votes) -> List[dict]:
    """
    interests: list of Interest ORM objects
    votes:     list of Vote ORM objects
    Returns list of match dicts sorted by score desc.
    """
    from collections import defaultdict
    # Index interests by normalised employee name
    idx = defaultdict(list)
    for i in interests:
        idx[_normalize(i.employee)].append(i)

    matches = []
    for vote in votes:
        if not vote.employee or not vote.subject:
            continue
        key = _normalize(vote.employee)
        for interest in idx.get(key, []):
            if not interest.entity:
                continue
            s = compute_score(interest.entity, vote.subject)
            if s > 0:
                matches.append({
                    "employee":    vote.employee,
                    "entity":      interest.entity,
                    "entity_type": interest.inv_type or "",
                    "subject":     vote.subject,
                    "vote_date":   vote.vote_date or "",
                    "score":       round(s * 100),
                    "likelihood":  likelihood(s),
                })

    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches
