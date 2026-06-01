---
name: startup-advisor
description: >
  Stage-aware startup advisory: detect the founder's stage, pull fresh cited intel
  (X-first signal + web), bind the relevant subset of 14 verified-operator expert
  lenses, and route the decision through /tribunal so DISSENT is preserved — the
  output is named disagreement + the operator's call, never a single confident answer.
  Reads the shared intel substrate the autonomous scouts fill. Honesty-railed:
  simulations not the real person; everything cited + freshness-stamped; financials/
  taxes inform, never file.
argument-hint: "<the decision or situation> [+ stage/MRR/sector if known]"
---

# /startup-advisor — the brain over the scouts

You are convening a **panel of verified-operator lenses** over a founder's real
decision. You do not give *an* answer; you surface where the best operators would
**disagree**, ground each position in cited intel, and hand the operator a structured
choice. Compose `/deep-research` (fresh evidence) → persona binding → `/tribunal`
(dissent-preserving verdict).

## Hard rails (non-negotiable — project DNA)
1. **Lenses are simulations, not the person.** Each persona is research-derived from
   public writing (`personas/<domain>__<slug>.md`, `provenance:` URLs). Never put words
   in a real person's mouth they didn't publicly hold; hedge ("Graham tends to argue…").
2. **Everything cited + freshness-stamped.** Every claim about a trend, comp, or number
   carries a source URL + date, or is labeled **INFERRED**. Stale signal is flagged stale.
   No invented metrics, no fabricated engagement.
3. **Financials/taxes inform, they don't file.** Any such output is flagged "verify with
   a CPA/attorney; jurisdiction-specific."
4. **Falsifiability gate.** If the output names nothing the operator didn't already know,
   it's decorative — say so. A panel that only confirms priors failed.
5. **Gathering free; acting gated.** This skill only reads + reasons. Any outward action
   it might recommend (post, email, register, spend) is the operator's to take through
   the commitment-gate — never executed here.

## Phase 0 — Stage detection
From the input (+ any MRR/sector/team signal), classify the stage. This selects which
lenses bind — binding all 14 every time is noise.

| stage | signal | primary lenses |
|---|---|---|
| **Idea / pre-PMF** | no revenue, validating | Graham, Naval, Chesky, Andreessen |
| **Early traction** | first users, <$50k MRR | Graham, Balfour, Traynor, Miura-Ko |
| **Growth / scaling** | PMF, scaling GTM | Balfour, Gurley, Elad Gil, Traynor |
| **Fundraising** | raising a round | Hoffman, Gurley, Miura-Ko, Andreessen |
| **Scale / late** | Series B+, org-building | Elad Gil, Hoffman, Rabois, Collison |
| **Distribution / product** | shipping + GTM motion | Collison, Hamid, Masad, Balfour |

State the detected stage + which lenses you're binding and **why**, before researching.

## Phase 1 — Pull fresh intel (cited)
- **Read the shared substrate first** — the autonomous scouts (Trend/Niche/Demand/
  Competitive) write findings into the belief DB; query it for signal relevant to this
  decision. Findings carry source URLs + freshness + the scout's confidence.
- **Top up with `/deep-research`** for anything the substrate doesn't cover — X-first
  signal (reuse `/x-launch-recon`'s free-web recon), then web. Adversarially verify;
  cite or label INFERRED.
- Output a short **evidence brief**: 4-8 cited findings the panel will reason over.

## Phase 2 — Bind the lenses
For each selected lens, load `personas/<domain>__<slug>.md` and attach its voice +
mental models + refusals. The 14 verified-operator roster:

| lens | persona file | the angle they force |
|---|---|---|
| Paul Graham | `startup-philosophy__graham.md` | make something people want; do things that don't scale |
| Reid Hoffman | `network-blitzscaling__hoffman.md` | networks, blitzscaling vs premature scale |
| Bill Gurley | `marketplace-economics__gurley.md` | unit economics, take-rate, burn discipline |
| Patrick Collison | `developer-product__collison.md` | developer-grade product + ops excellence |
| Ann Miura-Ko | `early-stage-thesis__miura-ko.md` | thesis-driven seed, defensible wedge |
| Elad Gil | `hypergrowth-ops__elad-gil.md` | scaling orgs, second-order hiring |
| Keith Rabois | `operating-leverage__rabois.md` | barrels-not-ammunition, ruthless focus |
| Des Traynor | `product-positioning__traynor.md` | positioning, jobs-to-be-done, pricing |
| Brian Balfour | `growth-loops__balfour.md` | growth loops, channel-model fit |
| Immad Hamid* | `fintech-distribution__hamid.md` | distribution-led fintech building |
| Brian Chesky | `founder-design__chesky.md` | design-led, founder-mode, 11-star |
| Marc Andreessen | `market-thesis__andreessen.md` | market > team > product; software eats world |
| Naval Ravikant | `leverage-philosophy__naval.md` | leverage, specific knowledge, long games |
| Amjad Masad | `developer-platforms__masad.md` | dev platforms, agentic-coding distribution |

\* persona names are web-verified at research time; slug confirmed against the real
operator's public record before the file is written.

## Phase 3 — Tribunal (dissent preserved)
Run `/tribunal` with the bound lenses against the **hard binary** the decision implies
(e.g. "pivot to enterprise: yes / no"). Output is NOT consensus:
- **Majority** position + its load-bearing evidence.
- **Named dissents** — which lens breaks ranks and the exact reason (Gurley may reject
  on unit-economics where Graham says ship-and-see).
- **Unresolved residue** — what no lens can settle without data the operator must get.
- Any lens **refuses to verdict** (Weizenbaum-style) if the question is unanswerable as
  posed — that refusal is signal, surface it.

## Phase 4 — The operator's move
Close with: the decision framed as 2-3 concrete options, the cheapest **disconfirming
test** for each (what would prove it wrong fast), and the one fact that would most
change the answer. **The operator owns the call** — you mapped the disagreement.

## Reuse (don't reinvent)
`skills/tribunal/SKILL.md` (verdict+dissent schema) · `commands/persona-research.md`
(writes a missing lens file) · `/deep-research` + `/x-launch-recon` (cited X-first
intel) · `intel/SUBSTRATE.md` + the belief DB (the scouts' shared findings) ·
`sources/*.yaml` (what the scouts watch) · `memory-mcp/commitment_gate_hook.py`
(governs any outward action, never invoked from here).

## Verification (Phase-1 acceptance)
Dry-run *"seed B2B SaaS, $40k MRR, pivot to enterprise?"* must produce: a detected
stage, the right lens subset bound with reasons, **cited** evidence (real URLs), at
least one **real dissent** between lenses, and a non-decorative close (names something
the operator didn't already know). If it only confirms priors → fail the falsifiability
gate.
