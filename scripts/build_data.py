#!/usr/bin/env python3
"""Build Anticipaid's static market-comparison snapshot.

The matcher is intentionally conservative. It produces lexical candidate equivalences,
not claims that venue settlement semantics are identical.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import heapq
import json
import math
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

UA = "anticipaid/0.1 (+https://anticipaid.com)"
KALSHI_URL = "https://external-api.kalshi.com/trade-api/v2/markets"
KALSHI_EVENTS_URL = "https://external-api.kalshi.com/trade-api/v2/events"
POLY_URL = "https://gamma-api.polymarket.com/markets"
POLY_KEYSET_URL = "https://gamma-api.polymarket.com/markets/keyset"
STOP = {
    "a","an","and","are","as","at","be","before","by","did","do","does","for","from","has","have","how",
    "in","is","it","of","on","or","the","to","was","were","what","when","where","which","who","will","with",
    "yes","no","market","markets","price","chance","probability"
}
WORD_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
DEADLINE_YEAR_RE = re.compile(r"\b(?:before|by|until|through|no later than|deadline|expire(?:s|d)?|expiration)\b.{0,48}?\b((?:19|20)\d{2})\b", re.IGNORECASE)


def get_json(url: str, params: dict | None = None, retries: int = 3):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=35) as r:
                return json.load(r)
        except Exception as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last


def fnum(value, default=None):
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def normalize(text: str) -> str:
    words = WORD_RE.findall((text or "").lower().replace("’", "'"))
    return " ".join(w for w in words if w not in STOP)


def tokens(text: str) -> set[str]:
    return set(normalize(text).split())


def nums(text: str) -> set[str]:
    return set(NUM_RE.findall((text or "").lower()))


def deadline_years(text: str) -> set[str]:
    return set(DEADLINE_YEAR_RE.findall(text or ""))


def parse_iso(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def deadline_delta_days(a, b):
    da, db = parse_iso(a), parse_iso(b)
    if not da or not db:
        return None
    return abs((da - db).total_seconds()) / 86400


def kalshi_probability(m):
    bid, ask = fnum(m.get("yes_bid_dollars")), fnum(m.get("yes_ask_dollars"))
    last = fnum(m.get("last_price_dollars"))
    if bid is not None and ask is not None and bid > 0 and ask > 0 and ask >= bid:
        return (bid + ask) / 2
    if last is not None and 0 <= last <= 1:
        return last
    if ask is not None and 0 <= ask <= 1:
        return ask
    if bid is not None and 0 <= bid <= 1:
        return bid
    return None


def parse_jsonish(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []


def poly_probability(m):
    outcomes = parse_jsonish(m.get("outcomes"))
    prices = parse_jsonish(m.get("outcomePrices"))
    if len(outcomes) != len(prices) or len(outcomes) != 2:
        return None
    lowered = [str(x).strip().lower() for x in outcomes]
    if "yes" not in lowered or "no" not in lowered:
        return None
    p = fnum(prices[lowered.index("yes")])
    return p if p is not None and 0 <= p <= 1 else None


def fetch_kalshi(max_items=10000):
    """Fetch open Kalshi markets with parent event context.

    The safety ceiling is deliberately high. A returned truncation flag makes
    any remaining coverage limit explicit in the public snapshot.
    """
    out, cursor, truncated = [], None, False
    while True:
        params = {
            "limit": 200,
            "status": "open",
            "with_nested_markets": "true",
        }
        if cursor:
            params["cursor"] = cursor
        page = get_json(KALSHI_EVENTS_URL, params)
        events = page.get("events", [])
        for event in events:
            for market in event.get("markets", []) or []:
                if market.get("status") not in (None, "open", "active"):
                    continue
                enriched = dict(market)
                enriched["_event_title"] = event.get("title") or ""
                enriched["_event_sub_title"] = event.get("sub_title") or ""
                enriched["_event_category"] = event.get("category") or ""
                out.append(enriched)
                if len(out) >= max_items:
                    truncated = bool(page.get("cursor"))
                    return out[:max_items], truncated
        cursor = page.get("cursor")
        if not cursor or not events:
            return out, False


def fetch_poly(max_items=10000):
    """Fetch active Polymarket markets using keyset pagination.

    Gamma offset pagination hard-stops near 2,000 rows. The keyset endpoint
    uses after_cursor and avoids that boundary.
    """
    out, cursor, seen = [], None, set()
    page_size = 100
    while True:
        remaining = max_items - len(out)
        if remaining <= 0:
            return out[:max_items], True
        params = {
            "active": "true",
            "closed": "false",
            "limit": min(page_size, remaining),
            "order": "id",
            "ascending": "true",
        }
        if cursor:
            params["after_cursor"] = cursor
        page = get_json(POLY_KEYSET_URL, params)
        if not isinstance(page, dict):
            raise ValueError("unexpected Polymarket keyset response")
        chunk = page.get("markets", []) or []
        next_cursor = page.get("next_cursor")
        if not chunk:
            return out, False
        out.extend(chunk)
        if not next_cursor:
            return out, False
        if next_cursor in seen:
            # Defensive loop guard: preserve partial coverage and surface it.
            return out, True
        seen.add(next_cursor)
        cursor = next_cursor

def canonical_kalshi(m):
    # Preserve parent-event context for display/disambiguation, but score
    # explicit question-like market propositions on their own wording. This
    # avoids diluting near-identical propositions with umbrella-event prose.
    market_fields = [m.get("title"), m.get("subtitle"), m.get("yes_sub_title")]
    proposition = " ".join(dict.fromkeys(
        x.strip() for x in market_fields if isinstance(x, str) and x.strip()
    ))
    event_fields = [m.get("_event_title"), m.get("_event_sub_title")]
    context = " ".join(dict.fromkeys(
        x.strip() for x in event_fields if isinstance(x, str) and x.strip()
    ))
    title = " ".join(x for x in [context, proposition] if x)
    question_like = re.match(r"^(will|does|do|is|are|can|could|who|which|what|when|where|how)\b",
                             proposition.strip().lower() if proposition else "")
    match_text = proposition if question_like else title
    p = kalshi_probability(m)
    if p is None or not title:
        return None
    ticker = m.get("ticker") or ""
    event = m.get("event_ticker") or ticker
    return {
        "id": ticker,
        "title": title.strip(),
        "match_text": match_text.strip(),
        "context": context.strip(),
        "rules_primary": (m.get("rules_primary") or "").strip(),
        "rules_secondary": (m.get("rules_secondary") or "").strip(),
        "early_close_condition": (m.get("early_close_condition") or "").strip(),
        "probability": p,
        "volume": fnum(m.get("volume_fp"), 0) or 0,
        "close_time": m.get("close_time") or m.get("expected_expiration_time"),
        "url": f"https://kalshi.com/markets/{urllib.parse.quote(str(event).lower())}",
    }


def canonical_poly(m):
    q = m.get("question") or m.get("title")
    p = poly_probability(m)
    if p is None or not q:
        return None
    slug = m.get("slug") or ""
    return {
        "id": str(m.get("id") or m.get("conditionId") or slug),
        "question": q.strip(),
        "description": (m.get("description") or "").strip(),
        "resolution_source": (m.get("resolutionSource") or m.get("resolvedBy") or "").strip(),
        "probability": p,
        "volume": fnum(m.get("volumeNum"), 0) or fnum(m.get("volume"), 0) or 0,
        "end_time": m.get("endDate") or m.get("end_date_iso"),
        "url": f"https://polymarket.com/event/{urllib.parse.quote(str(slug))}" if slug else "https://polymarket.com/",
    }


def match_score(a: str, b: str, a_deadline=None, b_deadline=None):
    na, nb = normalize(a), normalize(b)
    ta, tb = set(na.split()), set(nb.split())
    if not ta or not tb:
        return 0.0
    na_nums, nb_nums = nums(a), nums(b)
    if na_nums and nb_nums and na_nums != nb_nums:
        return 0.0
    inter = ta & tb
    if len(inter) < 2:
        return 0.0
    jacc = len(inter) / len(ta | tb)
    coverage = len(inter) / min(len(ta), len(tb))
    seq = difflib.SequenceMatcher(None, na, nb).ratio()
    score = 0.46 * jacc + 0.34 * seq + 0.20 * coverage
    dd = deadline_delta_days(a_deadline, b_deadline)
    if dd is not None:
        if dd <= 1:
            score += 0.04
        elif dd > 31:
            score -= 0.06
    return max(0.0, min(1.0, score))


def diagnose_candidates(kalshi, poly, limit=20):
    """Return strongest lexical near-matches with bounded memory."""
    pindex = defaultdict(set)
    for i, p in enumerate(poly):
        for t in tokens(p["question"]):
            if len(t) >= 3:
                pindex[t].add(i)

    top = []
    serial = 0
    for k in kalshi:
        candidate_ids = defaultdict(int)
        for t in tokens(k.get("match_text") or k["title"]):
            for i in pindex.get(t, ()):
                candidate_ids[i] += 1
        for i, count in candidate_ids.items():
            if count < 2:
                continue
            p = poly[i]
            score = match_score(
                k.get("match_text") or k["title"], p["question"],
                k.get("close_time"), p.get("end_time")
            )
            item = (score, serial, k["title"], p["question"])
            serial += 1
            if len(top) < limit:
                heapq.heappush(top, item)
            elif score > top[0][0]:
                heapq.heapreplace(top, item)

    top.sort(key=lambda x: x[0], reverse=True)
    return [
        {"score": round(score, 4), "kalshi": kt, "polymarket": pt}
        for score, _, kt, pt in top
    ]

def _full_terms(k, p):
    ktext = " ".join(x for x in [
        k.get("context"), k.get("match_text"), k.get("rules_primary"),
        k.get("rules_secondary"), k.get("early_close_condition")
    ] if x)
    ptext = " ".join(x for x in [
        p.get("question"), p.get("description"), p.get("resolution_source")
    ] if x)
    return ktext, ptext


def _stance(text, terms):
    """Return -1 for explicit exclusion, +1 for explicit inclusion, else 0."""
    s = (text or "").lower()
    if not any(t in s for t in terms):
        return 0
    term = r"(?:acting|interim|caretaker)"
    negative = [
        rf"{term}.{{0,80}}(?:will not|won't|do not|does not|not)\s+(?:count|qualify|include)",
        rf"(?:will not|won't|do not|does not|not)\s+(?:count|qualify|include).{{0,80}}{term}",
        rf"(?:exclude|excluding|excluded).{{0,80}}{term}",
    ]
    positive = [
        rf"{term}.{{0,80}}(?:count|counts|qualify|qualifies|include|included)",
        rf"(?:count|counts|qualify|qualifies|include|included).{{0,80}}{term}",
    ]
    if any(re.search(pat, s) for pat in negative):
        return -1
    if any(re.search(pat, s) for pat in positive):
        return 1
    return 0


def semantic_conflicts(k, p):
    """Conservative deterministic incompatibility checks.

    Passing these checks is not proof of settlement equivalence.
    """
    reasons = []
    ktext, ptext = _full_terms(k, p)

    ky, py = deadline_years(ktext), deadline_years(ptext)
    if ky and py and ky.isdisjoint(py):
        reasons.append(
            "explicit deadline years differ "
            f"(Kalshi {', '.join(sorted(ky))}; Polymarket {', '.join(sorted(py))})"
        )

    dd = deadline_delta_days(k.get("close_time"), p.get("end_time"))
    if dd is not None and dd > 370:
        reasons.append(f"scheduled end times differ by about {round(dd)} days")

    ks = _stance(ktext, ("acting", "interim", "caretaker"))
    ps = _stance(ptext, ("acting", "interim", "caretaker"))
    if ks and ps and ks != ps:
        reasons.append("acting/interim/caretaker treatment conflicts")

    return reasons


def build_pairs(kalshi, poly):
    pindex = defaultdict(set)
    for i, p in enumerate(poly):
        for t in tokens(p["question"]):
            if len(t) >= 3:
                pindex[t].add(i)

    matches, withheld = [], []
    used_poly = set()

    for k in sorted(kalshi, key=lambda x: x.get("volume", 0), reverse=True):
        kt = tokens(k.get("match_text") or k["title"])
        candidate_ids = defaultdict(int)
        for t in kt:
            for i in pindex.get(t, ()):
                candidate_ids[i] += 1

        candidates = []
        for i, count in candidate_ids.items():
            if count < 2:
                continue
            p = poly[i]
            score = match_score(
                k.get("match_text") or k["title"], p["question"],
                k.get("close_time"), p.get("end_time")
            )
            if score < 0.76:
                continue
            gap = abs(k["probability"] - p["probability"])
            conflicts = semantic_conflicts(k, p)
            candidates.append((score, gap, i, p, conflicts))

        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        chosen = None
        for candidate in candidates:
            score, gap, i, p, conflicts = candidate
            if not conflicts and i not in used_poly:
                chosen = candidate
                break

        if chosen:
            score, gap, i, p, conflicts = chosen
            used_poly.add(i)
            matches.append({
                "display_question": k["title"],
                "match_score": round(score, 4),
                "gap": round(gap, 4),
                "compatibility": "unblocked_candidate",
                "note": "No automated incompatibility rule fired; settlement equivalence remains unproven.",
                "kalshi": k,
                "polymarket": p,
            })
        elif candidates:
            score, gap, i, p, conflicts = candidates[0]
            withheld.append({
                "display_question": k["title"],
                "match_score": round(score, 4),
                "gap": round(gap, 4),
                "compatibility": "withheld",
                "reasons": conflicts or ["candidate consumed by a stronger one-to-one match"],
                "kalshi": k,
                "polymarket": p,
            })

    matches.sort(key=lambda x: (x["gap"], x["match_score"]), reverse=True)
    withheld.sort(key=lambda x: (x["match_score"], x["gap"]), reverse=True)
    return matches[:100], withheld[:100]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="site/data/latest.json")
    args = ap.parse_args()

    source = {"kalshi": {"ok": False}, "polymarket": {"ok": False}}
    raw_k, raw_p = [], []
    try:
        raw_k, k_truncated = fetch_kalshi()
        source["kalshi"] = {"ok": True, "count": len(raw_k), "truncated": k_truncated}
    except Exception as e:
        source["kalshi"] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:240]}
    try:
        raw_p, p_truncated = fetch_poly()
        source["polymarket"] = {"ok": True, "count": len(raw_p), "truncated": p_truncated}
    except Exception as e:
        source["polymarket"] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:240]}

    k = [x for x in (canonical_kalshi(m) for m in raw_k) if x]
    p = [x for x in (canonical_poly(m) for m in raw_p) if x]
    if k and p:
        pairs, withheld = build_pairs(k, p)
    else:
        pairs, withheld = [], []
    diagnostics = diagnose_candidates(k, p) if k and p else []
    print(json.dumps({"top_candidate_scores": diagnostics}, indent=2))
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "method_version": "lexical-plus-semantic-guard-v2",
        "stats": {
            "kalshi_open": len(k),
            "polymarket_open": len(p),
            "comparable_candidates": len(pairs),
            "withheld_candidates": len(withheld),
        },
        "sources": source,
        "pairs": pairs,
        "withheld_candidates": withheld,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "stats": payload["stats"], "sources": source}, indent=2))
    if not (source["kalshi"]["ok"] or source["polymarket"]["ok"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
