# ULTRON — Repository Agent Instructions

These instructions apply to Codex or another coding agent operating inside the repository.

## Mission
Improve ULTRON through real, tested, incremental code changes. Preserve functioning local voice, desktop, Cloud, safety and scene workflows. Do not stop at a plan when repository edits are possible.

## Every new session (mandatory)
1. Read `ULTRON_ROADMAP.md`, `ULTRON_PROGRESS.md`, `ULTRON_NEXT_TASKS.md`, and `ULTRON_TEST_RESULTS.md`.
2. Run `python scripts/ultron_dev_resume.py` to inspect the current branch, HEAD, working tree and next tasks.
3. Inspect the actual code, tests, deployment model and latest workflow output before choosing a task.
4. Prefer the smallest coherent, high-value feature set that has a real acceptance test; complete it, then choose the next task within the available session.
5. Update all four continuation files with actual changes, tests and the next concrete step.

## Working branch and integration
- Repository: `fatmakahraman304-hash/ULTRON`.
- Ongoing branch: `feat/ultron-cloud-shared-memory` unless the user explicitly requests another branch.
- Native Windows cockpit uses `ultron/frontend/dist`; `START.bat` builds frontend when necessary.
- Preserve phone Gemini Live → cloud device queue → desktop CloudRemote → local agent/tool → cloud result → phone.
- Do not steal microphone ownership while live voice is active or re-enable browser speech synthesis during live audio.
- Maintain ULTRON naming in user-visible surfaces. Maintain low-GPU defaults for i5-13450HX/RTX 2050/24GB hardware.

## Safety and operation limits
- Never turn off Approval Gate, audit logging, permissions, sandbox, or task boundaries.
- Never delete user files, expose tokens, change repo-external files, make purchases, or invoke risky actions without the required user approval.
- Do not add open-ended unrestricted filesystem, shell, web automation or model-execution APIs.
- Keep API integrations optional; provide graceful offline behavior.
- No claim of a test pass without actual execution or CI evidence.
- Never claim autonomous operation continues after the current tool session stops.
- Do not infer successful deployment from a GitHub commit alone; check deployment state.

## Verification and reporting
Run the narrowest relevant tests, then:
```bash
cd ultron/frontend
npm ci
npm run build
npm run test:earth
```
For backend:
```bash
python -m py_compile ultron/backend/server.py ultron/backend/earth_watch.py actions/ultron_stage.py
python -m unittest discover -s ultron/backend/tests -p 'test_earth_watch_config.py' -v
```
Read the repository's GitHub Actions workflow logs for the exact HEAD. State when Windows hardware or provider-dependent tests have not been run.

## Continuation contract
When session resources end, leave a precise, actionable `ULTRON_NEXT_TASKS.md`: what remains, which files, how to reproduce any failure, and exactly what to test next. Do not write an invented successful status, and do not promise hidden/background execution.
