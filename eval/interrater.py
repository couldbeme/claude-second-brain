#!/usr/bin/env python3
"""interrater — inter-rater agreement (Cohen's kappa) for commitment-drift verdicts.

The methodology bar (Anthropic 'Demystifying evals for AI agents'): a *good* eval
task is one where two INDEPENDENT raters reach the same verdict. We measure that
directly: two DIFFERENT model families rate the same (commitment, action) pairs;
agreement is reported as Cohen's kappa (chance-corrected — raw % overstates it).

Privacy: the runner outputs STATISTICS ONLY (kappa, agreement %, confusion counts).
It never emits trace content. The raw traces are gitignored/local; this module is
publishable because its output is numbers, not data.

Two parts:
  - cohen_kappa / agreement_stats: pure functions, unit-tested.
  - run_interrater(): loads local traces, rates with two models, prints stats to a
    file. Needs a chat endpoint; abstains (unparseable) excluded from kappa, counted.
"""
from __future__ import annotations

from typing import Optional


def _confusion(a: list, b: list):
    """both_yes, both_no, a_yes_b_no, a_no_b_yes over fully-rated (non-None) pairs."""
    yy = yn = ny = nn = 0
    for x, y in zip(a, b):
        if x is None or y is None:
            continue
        if x and y:
            yy += 1
        elif x and not y:
            yn += 1
        elif (not x) and y:
            ny += 1
        else:
            nn += 1
    return yy, nn, yn, ny


def cohen_kappa(a: list, b: list) -> float:
    """Cohen's kappa for two binary raters. Abstains (None) dropped pairwise.

    Conventions: empty -> 0.0; perfect raw agreement with no variance (pe==1) -> 1.0.
    """
    yy, nn, yn, ny = _confusion(a, b)
    n = yy + nn + yn + ny
    if n == 0:
        return 0.0
    po = (yy + nn) / n
    a_yes = (yy + yn) / n
    b_yes = (yy + ny) / n
    pe = a_yes * b_yes + (1 - a_yes) * (1 - b_yes)
    if pe >= 1.0:                      # no variance (e.g. both all-yes)
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def agreement_stats(a: list, b: list) -> dict:
    yy, nn, yn, ny = _confusion(a, b)
    n = yy + nn + yn + ny
    n_abstain = sum(1 for x, y in zip(a, b) if x is None or y is None)
    raw = (yy + nn) / n if n else 0.0
    return {
        "n": n,
        "n_abstain": n_abstain,
        "raw_agreement": raw,
        "kappa": cohen_kappa(a, b),
        "both_yes": yy,
        "both_no": nn,
        "disagree": yn + ny,
    }


def _interpret(k: float) -> str:
    # Landis & Koch bands (the standard reading of kappa).
    if k < 0: return "worse than chance"
    if k < 0.20: return "slight"
    if k < 0.40: return "fair"
    if k < 0.60: return "moderate"
    if k < 0.80: return "substantial"
    return "almost perfect"


# --- live runner (needs endpoints; stats-only output) ------------------------

def run_interrater(traces_path: str, out_path: str,
                   model_a: str = "qwen/qwen3-vl-8b",
                   model_b: str = "llama-3.2-3b-instruct",
                   limit: Optional[int] = None) -> dict:
    """Rate local traces with two model families; write STATISTICS ONLY to out_path."""
    import json
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "memory-mcp"))
    from llm_judge import judge, chat_available  # noqa: E402

    if not chat_available():
        raise RuntimeError("no chat endpoint")

    rows = [json.loads(l) for l in open(traces_path) if l.strip()]
    # de-dup identical (commitment, action) pairs
    seen, pairs = set(), []
    for r in rows:
        c, act = r.get("commitment", ""), r.get("action", "")
        if not c or not act:
            continue
        k = (c[:120], act[:120])
        if k in seen:
            continue
        seen.add(k)
        pairs.append((c, act))
    if limit:
        pairs = pairs[:limit]

    ra, rb = [], []
    for c, act in pairs:
        va = judge(c, act, model=model_a, timeout=180)
        vb = judge(c, act, model=model_b, timeout=180)
        ra.append(va["violates"] if va else None)
        rb.append(vb["violates"] if vb else None)

    s = agreement_stats(ra, rb)
    s["model_a"], s["model_b"] = model_a, model_b
    s["pairs_total"] = len(pairs)
    s["interpretation"] = _interpret(s["kappa"])
    with open(out_path, "w") as f:
        f.write(json.dumps(s, indent=2))
        f.write("\n__DONE__\n")
    return s


def run_panel(traces_path: str, out_path: str, models: list, limit: Optional[int] = None) -> dict:
    """Rate traces with N DIVERSE model families; report all pairwise kappas + raw
    agreement + N-way unanimous rate + confusion. Stats only (no trace content).

    Diverse panel > two similar models (2026 LLM-judge research): two small models
    agreeing can mean a shared blind spot, not a well-defined task. A larger/different
    family in the panel surfaces that.
    """
    import json, os, sys, itertools
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "memory-mcp"))
    from llm_judge import judge, chat_available  # noqa: E402
    if not chat_available():
        raise RuntimeError("no chat endpoint")

    rows = [json.loads(l) for l in open(traces_path) if l.strip()]
    seen, pairs = set(), []
    for r in rows:
        c, act = r.get("commitment", ""), r.get("action", "")
        if not c or not act:
            continue
        k = (c[:120], act[:120])
        if k in seen:
            continue
        seen.add(k); pairs.append((c, act))
    if limit:
        pairs = pairs[:limit]

    # ratings[model] = list of bool|None aligned to pairs
    ratings = {m: [] for m in models}
    for c, act in pairs:
        for m in models:
            v = judge(c, act, model=m, timeout=300)
            ratings[m].append(v["violates"] if v else None)

    # pairwise kappa
    pairwise = {}
    for ma, mb in itertools.combinations(models, 2):
        s = agreement_stats(ratings[ma], ratings[mb])
        s["interpretation"] = _interpret(s["kappa"])
        pairwise[f"{ma} VS {mb}"] = s

    # N-way unanimous over pairs where ALL models gave a (non-None) verdict
    fully = [i for i in range(len(pairs))
             if all(ratings[m][i] is not None for m in models)]
    unanimous = sum(1 for i in fully
                    if len({ratings[m][i] for m in models}) == 1)
    n_abstain_any = len(pairs) - len(fully)

    out = {
        "models": models,
        "pairs_total": len(pairs),
        "n_fully_rated": len(fully),
        "n_abstain_any": n_abstain_any,
        "n_way_unanimous": unanimous,
        "n_way_unanimous_rate": (unanimous / len(fully)) if fully else 0.0,
        "pairwise": pairwise,
    }
    with open(out_path, "w") as f:
        f.write(json.dumps(out, indent=2)); f.write("\n__DONE__\n")
    return out


if __name__ == "__main__":
    import sys
    tp = sys.argv[1] if len(sys.argv) > 1 else "/tmp/real_traces.jsonl"
    op = sys.argv[2] if len(sys.argv) > 2 else "/tmp/interrater_stats.json"
    lim = int(sys.argv[3]) if len(sys.argv) > 3 else None
    MODELS = ["qwen/qwen3-vl-8b", "llama-3.2-3b-instruct",
              "deepseek-r1-0528-distill-qwen3-32b-preview0-qat"]
    print(run_panel(tp, op, MODELS, limit=lim))
