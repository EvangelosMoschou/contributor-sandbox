# Contributor Sandbox

Cost-efficient delegation of real development work to a cheap coding model, inside a
scrubbed, credential-free git worktree — with a measured cost model for the two delegation
designs and the safety machinery that makes unattended cheap-model execution safe.

Born out of a simple observation while contributing to a large agent-harness project:
**the expensive model's session is the scarce resource, and most of what an agent burns
tokens on is rediscovering a codebase it could have been handed.**

## The measurement that drove the design

Instrumenting a real delegation run (a 4-file bugfix handed to a cheap contributor model):

| Metric | Value |
|---|---|
| Tool calls made by the contributor | 88 |
| Contributor tokens consumed | **~15M** |
| Raw tool-output bytes actually pulled into context | **0.5 MB (~150K tokens)** |
| The other ~14.8M tokens | exploration, re-reading, re-deriving context the orchestrator already had |

The cheap model's inefficiency is nearly free (~$2 at contributor rates); the expensive
model's attention is not. Every design decision follows from that asymmetry.

## Two delegation designs

### Design 1 — Pre-digestion ("the orchestrator thinks, the contributor types")

The orchestrator embeds exact file contents, line numbers, and a surgical change spec into
the prompt, with an explicit *"context is complete — do not explore"* instruction.
Targeted effect: **15M → 2-4M contributor tokens** by eliminating re-discovery.

Best when: the orchestrator already knows the code, contributor latency matters, or the
task is precision-critical.

### Design 2 — Inverted ("the contributor does everything") — implemented here

The orchestrator does **only** three things: build the scrubbed sandbox, check
auth/safety, and do a lean final review (read the diff, one targeted test run,
red-on-bug proof for regression tests). The contributor discovers, explores, reads,
implements, tests, and commits — with a "WHAT, not HOW" task statement.

Best when: you want the expensive session untouched. Even a sloppy 15M-token run costs
~$2; a pre-digestion pass would have cost the orchestrator more than that while clogging
its context window. **The fix for expensive babysitting is not a smarter prompt — it is
less babysitting.**

`SKILL.md` in this repo is the working implementation of Design 2 (with Design 1's
pre-digestion variant included as an option), battle-tested on real contributions.

## Safety model (what makes unattended cheap models acceptable)

1. **Scrubbed worktree** — fresh `git worktree`, remotes stripped (contributor physically
   cannot push), git config scanned for tokens, secret pattern scan
   (`sk-…`, `ghp_…`, OAuth tokens, AWS keys, private key blocks) with known-fixture
   allowlisting, `.env` absence asserted.
2. **Credential-stripped launch** — `GH_TOKEN`/`GITHUB_TOKEN` unset for the child process;
   working directory locked to the sandbox.
3. **Guard file** — `SANDBOX.md` states the rules in the contributor's own context.
4. **Batched log monitoring** — periodic greps of the session JSONL for out-of-sandbox
   paths, credential-touching commands, and push attempts. Any hit = kill and report.
5. **Lean review before landing** — read the diff, run ONE targeted test, demand a
   red-on-bug proof for regression tests. CI re-runs the full suite authoritatively.

## Repository layout

```
SKILL.md                     The delegation skill (Design 2 default, Design 1 optional)
analysis/token-breakdown.py  Reconstructs the tool-call/token cost breakdown
                             from a coding-agent session log (JSON lines)
SAFETY.md                    The scrub + monitoring checklist, standalone
```

## Usage sketch

```bash
# 1. scrubbed sandbox
git worktree add "$SANDBOX" -b contributor/<task> origin/dev
git -C "$SANDBOX" remote remove origin

# 2. launch the contributor (credentials stripped)
env -u GH_TOKEN -u GITHUB_TOKEN \
  <agent-cli> run -m <contributor-model> --format json "$(cat task.md)" 2>&1 | tee session.jsonl

# 3. measure what it cost
python3 analysis/token-breakdown.py session.jsonl

# 4. lean review, then cherry-pick onto the real branch
```

## Results in practice

Delegating a multi-file regression fix with Design 2: the contributor produced a
review-clean fix with its own test suite and red-on-bug proof; orchestrator cost was the
sandbox build plus one diff review. The work landed through normal project review
(four review rounds, all findings addressed) — the delegation itself was never the
bottleneck.

## License

MIT — see [LICENSE](LICENSE).
