# Repository governance

- `main` is the sole integration/release branch.
- Changes enter through pull requests; direct pushes to `main` should be disabled in repository settings.
- Require CI and maintainer review where repository settings and plan permit.
- CODEOWNERS covers skills, legal policy, registry, and workflows.
- Never fabricate reviews or bypass protected-branch requirements.
- PRs must include evaluation results and a rights declaration.
- Release tags point to reviewed commits and include release notes.
- If protection cannot be enabled with available permissions/plan, document that limitation rather than claiming enforcement.
