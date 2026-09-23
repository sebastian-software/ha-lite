# Agent instructions

ha-lite is a headless device runtime reduced from Home Assistant Core, a Python 3
application. `CLAUDE.md` is a symlink to this file, so this is the one place
agent guidance lives — put new guidance here rather than in a tool-specific file.

## Project Language

- Everything written into the repository is in English: code, identifiers, comments, docstrings, tests, documentation, ADRs, commit messages, pull request titles and descriptions, and issues. Conversation may happen in any language; what lands in the repo is English. See `docs/adr/0013-english-is-the-project-language.md`.

## Architecture Decision Records

- `docs/adr/` records why the architecture is the way it is. The records are **living documents**: no date, no version, not append-only. When a decision has been carried out, or a record makes a claim the tree no longer supports, edit the record. Write a new record only when the decision itself changes, and mark the old one `Superseded by NNNN`. See `docs/adr/README.md`.

## Reduction gates

- ha-lite keeps Home Assistant's integration catalog and removes only product layers (ADR 0020). `script/ha_lite_closure.py` computes the protected core, keeps the excluded product layers out of the tree and rejects imports of anything that is gone; `script/ha_lite_trigger_targets.py` checks that advertised trigger and condition targets match what the code filters on. Both run in CI with `--check`; run them before pushing a change that adds, removes or rewires a component. See ADR 0020 and ADR 0011.
- Protect ha-lite by adding checks in files ha-lite owns rather than by editing upstream ones — every edited upstream line is a conflict on every future import. See ADR 0014.
- Declaring a root in `script/ha_lite_closure_config.json` and giving it a CI job in `.github/workflows/ha-lite-ci.yml` are one decision, not two.

## Git Commit Guidelines

- **Do NOT amend, squash, or rebase commits that have already been pushed to the PR branch after the PR is opened** - Reviewers need to follow the commit history, as well as see what changed since their last review

## Pull Requests

- Use `.github/PULL_REQUEST_TEMPLATE.md`: Summary, Changes, Validation, Issue. Fill Validation with the commands you actually ran and their result.

## Development Commands

- Run "python3" in current virtual environment to ensure the correct Python version is used for testing.
- When entering a new environment or worktree, run `script/setup` to set up the virtual environment with all development dependencies (pylint, pre-commit hooks, etc.). This is required before committing. If uv reports that no download was found for the required Python version, the environment is running an outdated version of uv; upgrade it with `curl -LsSf https://astral.sh/uv/install.sh | sh` and run `script/setup` again.
- .vscode/tasks.json contains useful commands used for development.
- After finishing a code session, run `uv run --no-sync prek run --all-files` to check for linting and formatting issues.

## Python Syntax Notes

- ha-lite targets Python 3.14 as its minimum version. Do not flag syntax or features that require Python 3.14 as issues, and do not suggest workarounds for older Python versions.
- Python 3.14 explicitly allows `except TypeA, TypeB:` without parentheses. Never flag this as an issue.
- Python 3.14 evaluates annotations lazily (PEP 649). Forward references in annotations do not need to be quoted — annotations can reference names defined later in the module without quoting them or using `from __future__ import annotations`. Do not flag unquoted forward references in annotations as issues.

## Testing

- Use `uv run --no-sync pytest` to run tests
- After modifying `strings.json` for an integration, regenerate the English translation file before running tests: `python3 -m script.translations develop --integration <integration_name>`. Tests load translations from the generated `translations/en.json`, not directly from `strings.json`.
- When writing or modifying tests, ensure all test function parameters have type annotations.
- Prefer concrete types (for example, `HomeAssistant`, `MockConfigEntry`, etc.) over `Any`.
- Prefer `@pytest.mark.usefixtures` over arguments, if the argument is not going to be used.
- Avoid using conditions/branching in tests. Instead, either split tests or adjust the test parametrization to cover all cases without branching.
- If multiple tests share most of their code, use `pytest.mark.parametrize` to merge them into a single parameterized test instead of duplicating the body. Use `pytest.param` with an `id` parameter to name the test cases clearly.
- We use Syrupy for snapshot testing. Leverage `.ambr` snapshots instead of repetitive and exhaustive generation of test data within Python code itself.
- Hardcoded `entity_id`s in tests are fine. If the same one is repeated, use a constant.

## Good practices

- Integrations with Platinum or Gold level in the Integration Quality Scale reflect a high standard of code quality and maintainability. When looking for examples of something, these are good places to start. The level is indicated in the manifest.json of the integration.
- When reviewing entity actions, do not suggest extra defensive checks for input fields that are already validated by Home Assistant's service/action schemas and entity selection filters. Suggest additional guards only when data bypasses those validators or is transformed into a less-safe form.
- When validation guarantees a dict key exists, prefer direct key access (`data["key"]`) instead of `.get("key")` so contract violations are surfaced instead of silently masked.
- Keep comments concise. Prefer one short line stating the non-obvious constraint, or no comment at all.
- Do not add comments that just restate the code on the following line(s) (e.g. `# Check if initialized` above `if self.initialized:`). Comments should only explain why (non-obvious constraints, surprising behavior, or workarounds), never what. Never add comments that justify a change by referencing what the code looked like before. Comments in tests that explain why a function call or assertion is made are ok.
- Do not add section or divider comments (e.g. `# --- XYZ Triggers ---`) inside or outside of functions, since those can easily become stale and be misleading.
- When catching exceptions, try-clauses should be as small as possible, i.e. avoid wrapping large blocks of code in a try-clause, and avoid catching exceptions from functions that are not expected to raise them.
- Sensitive service actions, i.e. those that can change configuration or have security implications, should require an admin user. Register them with the `async_register_admin_service` service helper, which checks this for you.
