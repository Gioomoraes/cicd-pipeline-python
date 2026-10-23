# cicd-pipeline-python

[![CI](https://github.com/Gioomoraes/cicd-pipeline-python/actions/workflows/ci.yml/badge.svg)](https://github.com/Gioomoraes/cicd-pipeline-python/actions/workflows/ci.yml)
[![Build](https://github.com/Gioomoraes/cicd-pipeline-python/actions/workflows/build.yml/badge.svg)](https://github.com/Gioomoraes/cicd-pipeline-python/actions/workflows/build.yml)
[![Deploy](https://github.com/Gioomoraes/cicd-pipeline-python/actions/workflows/deploy.yml/badge.svg)](https://github.com/Gioomoraes/cicd-pipeline-python/actions/workflows/deploy.yml)

An end-to-end CI/CD pipeline built with GitHub Actions: lint, tests, security scanning, a scanned Docker image published to GHCR, and a gated deploy to staging and production with smoke tests and automatic rollback.

> The Python API is intentionally tiny. The point of this project is the delivery pipeline around it, not the application.

## Pipeline overview

```mermaid
flowchart LR
    A[git push to main] --> B

    subgraph CI [CI workflow]
        B[lint<br/>ruff]
        C[test<br/>pytest, py3.11 and 3.12, coverage 80%+]
        D[security<br/>bandit, pip-audit, gitleaks]
    end

    B & C & D --> E

    subgraph BUILD [Build workflow]
        E[docker buildx build] --> F[Trivy scan<br/>CRITICAL and HIGH] --> G[push to GHCR<br/>short SHA and latest]
    end

    G --> H

    subgraph DEPLOY [Deploy workflow]
        H[staging<br/>kind cluster, rollout, smoke test] --> I{manual approval}
        I --> J[production<br/>kind cluster, rollout, smoke test]
        J --> K[GitHub Release<br/>generated notes]
    end

    H -. on failure .-> R[diagnostics and rollout undo]
    J -. on failure .-> R
```

The three workflows are chained with `workflow_run`, so each stage only starts after the previous one succeeded, and every stage works on the exact commit that passed the earlier checks.

| Workflow | Trigger | What it does |
|---|---|---|
| **CI** | push to `main`, pull requests | `ruff` lint and format check; `pytest` on Python 3.11 and 3.12 with a coverage gate of 80%; security job with `bandit`, `pip-audit` and `gitleaks`. Outdated runs are cancelled. |
| **Build** | CI succeeded on `main` | Builds the image once, scans it with Trivy (fails on fixable CRITICAL/HIGH findings), and only then pushes it to GHCR tagged with the short commit SHA and `latest`. |
| **Deploy** | Build succeeded | Deploys the image by SHA to **staging** automatically, runs a smoke test, then waits for a **manual approval** before deploying to **production**. On failure it prints diagnostics and runs `kubectl rollout undo`. On success the production job publishes a GitHub Release with generated notes. |
| **Dependabot** | weekly | Opens update PRs for `pip` and `github-actions`. Each PR runs the full CI. |

## Tech stack

Python 3.11/3.12, FastAPI, pytest, ruff, Docker (buildx, multi-stage image), GitHub Actions, GitHub Container Registry, Trivy, bandit, pip-audit, gitleaks, Dependabot, Kubernetes manifests, kind.

## Security checks

| Layer | Tool | Where |
|---|---|---|
| Secrets in git history | gitleaks | CI |
| Static analysis of the code | bandit | CI |
| Vulnerable dependencies | pip-audit, Dependabot | CI, weekly PRs |
| Vulnerable image contents | Trivy | Build, before the push |
| Workflow permissions | least privilege per workflow and job | all workflows |
| Production changes | required reviewer on the `production` environment | Deploy |

## Design decisions

- **Build once, scan before publishing.** The image is built and loaded locally, scanned, and only pushed if the scan passes. An unscanned image never reaches the registry.
- **Immutable tags.** Deployments use the commit SHA, not `latest`, so a deployed version always maps to one commit.
- **Smoke test as a gate.** `scripts/smoke_test.py` (standard library only) polls `/health` and checks that `/version` matches the commit being deployed. A wrong version fails the deploy.
- **Least privilege.** Workflows default to read-only permissions and only the jobs that need more (package writes, release creation) ask for it.
- **No context interpolation inside `run` blocks.** Values like the commit SHA are passed through `env`, which avoids script injection through workflow context.
- **Serialised deploys.** A `deploy` concurrency group prevents two deployments from running at the same time.

## Repository layout

```
.
├── .github/workflows/     # ci.yml, build.yml, deploy.yml
├── .github/dependabot.yml
├── .kiro/steering/        # rules given to the AI agent used to scaffold files
├── app/                   # FastAPI application
├── tests/                 # pytest suite
├── k8s/                   # Deployment and Service manifests
├── scripts/               # smoke_test.py, release_notes.py
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

## Run it locally

```bash
python -m venv .venv
source .venv/bin/activate          # Git Bash on Windows: source .venv/Scripts/activate
pip install -e ".[dev]"

ruff check .
ruff format --check .
pytest --cov=app --cov-fail-under=80

APP_VERSION=dev uvicorn app.main:app --port 8000
```

In another terminal, run the same smoke test the pipeline uses:

```bash
python scripts/smoke_test.py --url http://localhost:8000 --expected-version dev
```

With Docker installed:

```bash
docker compose up
```

## Challenges and lessons learned

Most of the AI-generated files needed a human review, and the pipeline itself caught the problems. These are the ones worth remembering.

- **Invalid build backend.** The generated `pyproject.toml` pointed to a build backend that does not exist, so `pip install` failed in CI. I reproduced it locally in a virtual environment and fixed the `[build-system]` block.
- **Python version mismatch.** `requires-python` said 3.12 while the CI matrix also tested 3.11, and pip refused to install on 3.11. I aligned both so the matrix keeps testing two versions.
- **The dependency scan found real vulnerabilities.** `pip-audit` reported 28 advisories across three packages (pip, pytest, starlette). Fixing starlette required upgrading FastAPI, because the pinned FastAPI version capped starlette below the fixed range. The pins in `pyproject.toml` were updated and the audit now passes.
- **Dependabot PRs need judgement.** CI was green on every PR, but the `uvicorn` bump was a big jump and the test client never starts a real server, so I started the app manually before merging it.
- **Supply-chain awareness.** The agent suggested an old Trivy action tag. That tag range was affected by a supply-chain incident in the action's repository and the tag no longer resolved. I switched to a version the maintainers state was not compromised. Pinning actions by full commit SHA is the stricter next step.
- **YAML indentation can invalidate a whole workflow.** One misplaced space made GitHub reject `build.yml` and show a failed run with no jobs. Validating the file locally with a YAML parser pointed to the exact line.
- **Lint caught a generated script.** The smoke test script broke the project's line-length rule, and CI blocked the pipeline before any image was built.
- **Cluster name mismatch.** `kind load` looked for a cluster named `kind`, while the kind action created one with a different default name. Setting `cluster_name` explicitly fixed it.

I built this with an AI coding agent on a small monthly credit budget. Prompts were scoped to one deliverable each, and failing CI logs were debugged outside the agent. The rules given to the agent are in `.kiro/steering/`.

## Limitations

- **The deploy is a simulation.** Staging and production run on an ephemeral `kind` cluster created inside the job and destroyed when it ends. There is no public URL. The production job deploys the same image into a fresh cluster rather than promoting a running staging environment.
- **Rollback is demonstrative.** `kubectl rollout undo` shows the mechanism, but it cannot protect a real environment here because the cluster does not outlive the job.
- **One push at a time.** The deploy workflow derives the image tag from the commit of the triggering run. Two pushes in quick succession could make the tags diverge and the image pull fail.
- **Actions are pinned by tag, not by SHA.**

## What's next

- Provision real infrastructure with Terraform and deploy to a managed Kubernetes cluster.
- Move to GitOps with ArgoCD.
- Add Prometheus and Grafana for metrics and alerts.
- Pin third-party actions by commit SHA.
