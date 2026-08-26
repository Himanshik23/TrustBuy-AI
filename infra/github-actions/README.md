# CI/CD workflows

GitHub Actions only ever reads workflow files from `.github/workflows/` at
the repo root - that's a GitHub platform requirement, not a convention we
can relocate. The actual pipeline lives at
[`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

This folder exists to keep the physical layout matching
[ARCHITECTURE.md](../../ARCHITECTURE.md) §7's `infra/github-actions/`
entry - treat it as the documented pointer to where CI configuration is
owned, not a second copy to keep in sync.
