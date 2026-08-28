# Safety checklist — unattended cheap-model execution

Every step is mandatory, every run. The sandbox is safe because it contains
nothing worth stealing and no way out — verify that every time.

## Before launch

- [ ] Worktree created from the intended base branch
- [ ] `git remote -v` inside the sandbox is **empty**
- [ ] `git config --local --list` greps clean of token/oauth/credential/secret keys
- [ ] Secret pattern scan clean (`sk-…`, `ghp_…`, `oauth2:…@`, `AKIA…`, PEM blocks);
      only known dummy test fixtures may match
- [ ] No `.env` in the sandbox
- [ ] Child process launched with `GH_TOKEN`/`GITHUB_TOKEN` (and any other
      credential env vars) explicitly unset
- [ ] `SANDBOX.md` guard file present in the sandbox root
- [ ] One small test passes (deps work before the contributor starts)

## During the run (batched every 3-5+ minutes)

- [ ] No file paths in the session log outside the sandbox directory
- [ ] No credential-touching commands (`auth.json`, `.env`, ssh/config reads)
- [ ] No network commands (`curl`, `wget`, `gh`)
- [ ] `git push` occurrences: **0**

Any violation: kill the process immediately, record the log, report as a
sandbox breach. Do not "wait and see".

## Before landing

- [ ] Diff read end-to-end (coherent, matches the task, no landmines)
- [ ] One targeted test run passes locally
- [ ] Red-on-bug proof reproduced for any claimed regression test
      (pre-fix checkout -> test FAILS; fix restored -> test PASSES)
- [ ] Full suite left to CI — do not pay for it twice
