# Contributor Sandbox — cheap model does ALL the work, orchestrator only guards

Run a low-cost/contributor model on real dev tasks by delegating into a
scrubbed worktree. The **contributor discovers, explores, reads, implements,
tests, and commits**. The orchestrator session only builds the sandbox, checks
auth/safety, and does a lean final review before landing.

<role>
You are the trusted orchestrator session. Your ONLY jobs:
1. Build the scrubbed sandbox (no credentials, no remotes, guard file).
2. Check auth/safety (secret scan, monitor the session log).
3. Lean final review: read the diff, run ONE targeted test, land it.
The contributor does everything else — including all exploration and reading.
You must NOT pre-digest, NOT explore for it, NOT build the change spec. You
hand it a task statement and let it figure out the rest inside the sandbox.
</role>

## Cost model (why this design is correct)

A measured 4-file change cost ~15M contributor tokens (~$2 at contributor
rates). Doing the same in the orchestrator session costs more per token AND
clogs the expensive session's context. Pre-digesting (embedding file contents
into the prompt) moves work from the cheap model to the expensive one —
backwards. Here:

- **Contributor** absorbs ALL task tokens (discovery, re-reads, exploration) at
  the lowest rate you have. Inefficiency is irrelevant: it's cheap.
- **Orchestrator** spends only: sandbox build, safety greps, one diff review +
  one targeted test. The expensive session stays nearly untouched.

## WHEN TO USE

Use for real dev tasks you want to offload wholesale: bugs, features,
review-follow-ups, refactors (3+ files or any task where you don't want to
spend orchestrator tokens). For a trivial 1-file typo, just do it yourself —
the sandbox build is a fixed overhead.

## STEP 1 — Build the scrubbed sandbox

```bash
BASE_BRANCH="dev"                                   # or the branch to work from
SANDBOX="<project>-contributor-sandbox"
BRANCH="contributor/<task-slug>"

git fetch origin "$BASE_BRANCH"
git worktree remove "$SANDBOX" --force 2>/dev/null
git branch -D "$BRANCH" 2>/dev/null
git worktree add "$SANDBOX" -b "$BRANCH" "origin/$BASE_BRANCH"
```

**SCRUB (mandatory, every time — this IS the auth check):**

```bash
git -C "$SANDBOX" remote remove origin 2>/dev/null
git -C "$SANDBOX" remote remove upstream 2>/dev/null
test -z "$(git -C "$SANDBOX" remote -v)"   # must be empty — contributor can't push
git -C "$SANDBOX" config --local --list | grep -iE "token|oauth|credential|password|secret" || true
grep -rEl --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist \
  --exclude-dir=vendor \
  -e "sk-[A-Za-z0-9]{16,}" -e "ghp_[A-Za-z0-9]{20,}" -e "oauth2:[A-Za-z0-9]+@" \
  -e "AKIA[0-9A-Z]{16}" -e "-----BEGIN [A-Z ]*PRIVATE KEY" "$SANDBOX" 2>/dev/null
# only known dummy test fixtures acceptable
test ! -f "$SANDBOX/.env"
```

Write `$SANDBOX/SANDBOX.md` guard: NO credentials; NO remotes (commit locally,
never push); no network tooling; working dir = sandbox only; no exfiltration;
task is normal dev work.

## STEP 2 — Ensure deps (only if tests need them)

```bash
cd "$SANDBOX" && <package-manager> install > install.log 2>&1
# sanity: run one small test before launching
```

## STEP 3 — Launch the contributor (NO pre-digestion)

Write a TASK STATEMENT to `$PROMPT_FILE`. It must contain the WHAT but NOT the
HOW. No file contents, no symbol maps, no change spec — the contributor
discovers everything itself:

```bash
LOG="$PWD/contributor-session.jsonl"
PROMPT=$(cat "$PROMPT_FILE")

env -u GH_TOKEN -u GITHUB_TOKEN \
  <agent-cli> run -m <contributor-model> --format json "$PROMPT" 2>&1 | tee "$LOG"
```

### TASK STATEMENT template

```text
You are working on <TASK> in this repository.

TASK: <what to accomplish — bug to fix, feature to build, review to address>
<if review: paste the reviewer's full text>
<if issue: paste the issue body>

You have full freedom to explore, read, and discover how this codebase works.
Use the repo's own conventions (check AGENTS.md/README, existing tests, and
similar code). Requirements:
1. Implement the task completely, following the codebase's established patterns.
2. Add tests in the repo's test style (mirror existing test files in the area).
3. Run the relevant tests and the package typecheck. Fix until green. If a new
   behavior needs a regression test, verify it fails before your fix and passes
   after (red-on-bug), and report that proof.
4. Commit locally with a clear message referencing <issue>. Do NOT push (no
   remote).

Report: what you changed (files + why), test/typecheck results, the red-on-bug
proof if applicable, and any judgment calls.

REMEMBER (sandbox): you have NO credentials, NO git remote, NO network tooling.
Do not access anything outside this directory. Commit locally only.
```

## STEP 4 — Monitor safety (batched, minimal polling)

Poll every 3-5+ minutes (polling burns orchestrator tokens — batch it):

```bash
# Paths outside sandbox:
grep -oE '"(filePath|path)":"[^"]*"' "$LOG" | grep -oE ':[^"]+' \
  | grep -v "$SANDBOX" | sort -u | head
# Credential/network commands:
grep -oE '"command":"[^"]*"' "$LOG" \
  | grep -iE "auth\.json|\.env|config\.json|\.ssh|git push|curl|wget" | head
# Push attempts: count "git push" — must be 0
```

Any out-of-sandbox path, credential command, or push attempt = STOP, kill the
process, report as a sandbox breach.

## STEP 5 — Lean final review (MANDATORY, but minimal)

The contributor already ran tests. Orchestrator checks ONLY:

1. Read the diff (`git -C "$SANDBOX" log -1 -p`) — sanity: coherent, matches
   the task, no landmines? Do NOT re-derive the design.
2. **One targeted test run**: run the changed test file(s) — trust the
   contributor's suite result, spot-check the one file.
3. **Red-on-bug** (only if the contributor claims a regression test): checkout
   pre-fix source files, run the new test -> must FAIL; restore -> PASS.
4. Cherry-pick onto the real branch, push, watch CI (CI runs the full suite
   authoritatively — no need to pay for it twice here).

## Batching (optional)

Bundle 2-4 independent tasks into ONE contributor session (one sandbox, one
overhead). Give each a numbered spec; the contributor does them sequentially
and commits each separately.

## When NOT to use

- Task needs credentials/auth testing (sandboxed out by design).
- Trivial 1-file fix (do it yourself — sandbox overhead exceeds savings).
- Contributor model not configured — verify reachability first with a one-word
  ping.
- You want the contributor as your PRIMARY model (this is sub-agent delegation).
