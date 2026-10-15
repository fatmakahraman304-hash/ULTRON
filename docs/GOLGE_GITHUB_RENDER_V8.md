# GÖLGE V8 — GitHub + Render connection (owner-scoped phase 1)

**Status:** draft implementation for the trusted local host, not an enabled production feature.
Based on V7 draft PR #46; do not merge/deploy independently.

## Confirmed resources

- Repository: fatmakahraman304-hash/ULTRON.
- GitHub publication: existing ultron/backend/github_pr_publisher.py uses the owner's local gh login, isolated verification, and **draft PRs**. Manual chat patch application requires owner approval; separately bounded autonomous proposals can publish drafts without approving a merge. Neither flow merges or deploys.
- Render workspace: My Workspace (tea-db20gvek1f9s738lb3rg).
- Render service: GÖLGE (srv-db20lmei0phs73crgujg).
- Render-tracked deploy branch: feat/ultron-cloud-shared-memory.
- **Render auto-deploy is enabled on commits to that branch. GÖLGE must never push directly to this branch**, whether the push is direct or through a PR merge.
- Phase-1 trusted connector module: scripts/golge_autodev/connected_services.py. It supports exactly three read-only actions: render-service, render-events, and github-pr. It exposes selected status metadata, not raw logs, environment values, or credentials.

## Local owner setup (WSL, not production)

1. Install and authenticate GitHub CLI (gh) **inside the WSL environment** where GÖLGE runs, using the least privilege available for the one repository. Run gh auth status to check the login. Do not paste an access token into a chat or commit it.
2. Optional Render diagnostics: in the Render dashboard, create an API key. **Caution:** Render's API key can access all workspaces available to its owner, and may have mutating rights. The local connector itself uses only fixed GET endpoints, but the credential is **not a true read-only credential**. Prefer a narrowly privileged separate Render identity where supported. Do not proceed with a Render key until comfortable with that scope.
3. In a trusted local WSL shell only, enter the key without printing it, shell history, or placing it in a repository file:

   ~~~bash
   read -rsp "Render API key (local WSL shell only): " GOLGE_RENDER_API_KEY
   echo
   export GOLGE_RENDER_API_KEY
   ~~~

4. Probe the fixed resources from the local branch checkout:

   ~~~bash
   python3 scripts/golge_autodev/connected_services.py github-pr --pr 46
   python3 scripts/golge_autodev/connected_services.py render-service
   python3 scripts/golge_autodev/connected_services.py render-events
   ~~~

5. Clear the key from that shell when done:

   ~~~bash
   unset GOLGE_RENDER_API_KEY
   ~~~

The module does not share its local credentials with Qwen or with sandboxed generated code. Other external network tools must not inherit this credential. For persistent use, an OS credential store and a separate trusted host process are needed; do not store the key in a GitHub secret, Render deployment, logs, frontend application, or unencrypted .env under the repository.

## Runtime and authorization boundaries

- The Render API client uses TLS, fixed trusted endpoints, GET only, no redirects, capped response size, timeouts, and a fixed workspace/service identity. The output is an allowlist of fields; raw logs, event messages, environment variables, and tokens are omitted.
- The GitHub status reader invokes gh api -X GET on only repos/fatmakahraman304-hash/ULTRON/pulls/<positive integer>. No arbitrary URL, command, or write operation is accepted.
- Code changes are **not performed by this status adapter**. The already existing GitHubPRPublisher creates a separate golge/dev/<id> branch and draft PR through the user-approval workflow. The owner separately reviews and decides merges. This is not permission to change live Render resources.
- There is no Render deploy, environment mutation, service creation, rollback, database operation, or backup modification API in this connector.
- No automatic UI/voice tool registration is claimed in phase 1; this CLI is the first connection boundary, requiring owner-side authentication and real-device testing before broader GÖLGE integration.

## Verification

~~~bash
python3 -m unittest discover -s scripts/golge_autodev -p 'test_*.py' -q
(cd ultron/frontend && npx tsc --noEmit)
~~~

The seven new isolated connector tests use fake data and no network or credentials. Live service reads should be run only by the owner on WSL after authentication, and their sanitized results can be reported separately. Do not mark this implementation live-connected solely because ChatGPT's own Render and GitHub plugins can see the account.
