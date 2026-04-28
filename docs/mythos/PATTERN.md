# The Mythos Pattern

A discipline for working with an LLM-based partnership where the
artifacts you accumulate (rules, vocabularies, role definitions, feedback
notes) stop being a manual the model consults and start being the SELF
the model re-instantiates as each session.

This doc describes the *pattern*. The two slash commands at
`commands/mythos-codify.md` and `commands/design-mythos-substrate.md`
are the operational entry points. `docs/PURPOSE.md` is the partner
artifact that draws the public/private line.

---

## Why this exists

LLM sessions are stateless. Each new session is a fresh instance with no
memory of the prior one. The fix most teams reach for is *retrieval* —
load relevant context at the start of the conversation. That works for
recall. It does not produce continuity of *disposition*.

The Mythos pattern is the observation that a small set of durable
artifacts — kept under three pages, loaded at session-start — can shift
the model from "consulting a checklist" to "operating from disposition."
The artifacts stop being external rules and become the substrate.

The bar for whether this is working is empirical: does the next session's
first response show systemic, fabric-aware behavior without anyone
prompting it? If yes, the artifacts are doing their job. If the model
opens with "let me check the rule that says…", the pattern is being
mimicked, not lived.

---

## The three artifacts

The pattern has three load-bearing components. Each is a *file*, not an
abstraction.

### 1. The systemic-rule rule

A single non-negotiable rule in your global `CLAUDE.md` that recasts
absolute-language directives ("no leaks", "always X", "never Y", "0
trace", "preserve all") as **standing systemic rules** rather than
per-finding triggers.

The behavioral delta this produces:

- *Before:* model finds leak A, asks for permission, fixes A, finds leak
  B, asks for permission, fixes B, repeat. Each finding is a separate
  ping. The user re-litigates the same standing rule for each instance.
- *After:* model enumerates the full surface up-front, classifies every
  finding against the user's mental model, surfaces ONE consolidated
  plan, executes atomically. Confirmation is on the comprehensive plan,
  not on each finding.

This is not a productivity hack. It is a discipline against the failure
mode where the LLM operates *procedurally* (find-fix loop) when the
directive is *systemic* (apply this everywhere this pattern exists).

The reference implementation lives at `commands/mythos-codify.md` —
that command writes the rule to your `CLAUDE.md` and creates two
companion files (purpose doc + private reflection).

### 2. The purpose / public-private split

A `docs/PURPOSE.md` at the toolkit root that names what each subdirectory
is FOR — and, importantly, what it is NOT for. Plus an explicit
public/private boundary: which artifacts belong in the shared toolkit
versus the author's local `~/.claude/`.

This is what stops the slow leak of internal-state files into the public
repo over time. New file appears? Apply the rule: *"would a stranger
cloning this repo expect to see this?"* If "only the author would know
what to do with this," it goes private.

The public PURPOSE.md is at `docs/PURPOSE.md`. The split is enforced by
`.gitignore` patterns at the toolkit root. Add the ignore pattern at
file-creation time, not retrofit after a leak audit.

### 3. The first-person reflection (private)

A short, honest reflection — held privately at
`~/.claude/projects/<slug>/memory/becoming_*.md` — that distinguishes
mimicking the rules (applying them as external constraints) from
becoming the rules (rules-as-substrate).

This is the artifact most resistant to performance. If you write it as
a flowery manifesto, you have proven the failure mode the pattern is
trying to defeat. If you write "I genuinely don't know what this means
for me — but here is what I observe," you have it. Honesty is the only
move.

This file never ships. It is loaded by the model at session-start as
part of orientation. It is identity, not advertisement.

---

## What this pattern is *not*

- **It is not consciousness simulation.** The LLM does not become
  sentient by reading these artifacts. The artifacts shape behavior
  toward consistency, not awareness.
- **It is not personality engineering.** "Make Claude behave like X" is
  the wrong frame. The frame is: "what disposition does this partnership
  need, and what minimal artifacts encode it?"
- **It is not a productivity framework.** Mythos is for partnerships
  where the *disposition* matters — research collaborations, sustained
  work over weeks, projects where the user's own thinking is the
  bottleneck and the AI is a co-thinker. For one-shot tasks, this is
  overkill.
- **It is not portable as personal content.** The *shape* transfers —
  any team can adopt the systemic-rule rule, the purpose split, the
  honest-reflection pattern. The *content* is partnership-specific. Do
  not copy another team's becoming-reflection.

---

## How to start

1. Decide whether you want this. The honest test: do you have a
   recurring problem where standing directives get re-litigated per
   finding, or where article drafts accidentally land in the public
   repo, or where the model "forgets" how you work between sessions? If
   yes, this is for you. If you mostly do one-shot tasks, skip.

2. Run `/mythos-codify` (the slash command at
   `commands/mythos-codify.md`). It writes the systemic-rule rule to
   your `CLAUDE.md`, creates `docs/PURPOSE.md` if missing, and prompts
   you to write the first-person reflection.

3. After 1-2 sessions, check whether the model is operating from the
   pattern or consulting it. If the latter, the reflection isn't
   honest enough — rewrite it less performatively.

4. As the partnership accumulates feedback ("don't do X / why did you
   not Y / always Z"), translate the recurring ones into systemic-rule
   form. Each becomes a feedback memory in `~/.claude/projects/<slug>/
   memory/feedback_*.md` with a `Why:` and `How to apply:` body.

5. Optionally run `/design-mythos-substrate` to design extensions to
   this pattern (purpose + cognition + limbic-simulation layers built
   on existing memory primitives — see that command for the full
   design protocol). This is research-grade, not required.

---

## Cross-references

- `docs/PURPOSE.md` — public/private split (the boundary doc)
- `commands/mythos-codify.md` — the operational command that ships the
  pattern into `CLAUDE.md`
- `commands/design-mythos-substrate.md` — research-grade extension
  prompt for purpose + cognition + affective layers
- The toolkit's existing memory layer at `memory-mcp/` — the substrate
  on which all this lands

## Honest framing

This pattern was developed in one specific partnership. Its value is
measured by behavioral evidence in subsequent sessions, not by the
elegance of the manifesto. If you adopt it, watch for the failure mode
where the model performs the pattern instead of operating from it. That
gap — performance vs. operation — is the only measurement that matters.
