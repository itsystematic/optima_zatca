# Contributing to Optima ZATCA

## Branches

| Branch | Frappe / ERPNext | Role | Changes arrive by |
|---|---|---|---|
| `develop` (default) | 16 | Where all work lands. Never deployed to a site. | PRs from fix and feature branches |
| `version-16` | 16 | Release branch for ERPNext 16 sites. Tags `v4.x.y`. | Release PRs from `develop`, version bumps |
| `version-15` | 15 | Maintenance branch for ERPNext 15 sites. Tags `v3.x.y`. | Backport PRs, v15-only fixes, version bumps |

```
fix / feat branch
      │ PR
      ▼
   develop ──── release PR (merge commit) ──────────────────────────────────► version-16   v4.x.y
      │
      └──── label "backport version-15": the bot cherry-picks, opens a PR ──► version-15   v3.x.y
```

Every change starts on `develop`. `version-16` receives all of it at the next release; `version-15` receives only what is labelled for it.

## Making a change

1. Branch from `develop`, named after the kind of change: `fix/csr-fields`, `feat/vat-report`.
2. Write commit messages as `type(scope): summary`. The type is one of `fix`, `feat`, `refactor`, `docs`, `test` or `chore`; the scope is the area in kebab-case; the summary is imperative, with no trailing period. For example: `fix(onboarding): keep the compliance key when a retry resumes`.
3. Open the PR into `develop`, with its title in the same format. Release notes are built from PR titles.
4. If ERPNext 15 sites need the change too, add the label `backport version-15` before merging.

Don't open PRs into `version-15` or `version-16`, except in the cases described under Backporting and Releasing.

## Backporting to version-15

What to backport:

- Bug fixes that affect v15 sites.
- Changes ZATCA requires (new rules, XML or API changes). Every site has to comply, whichever version it runs.

What not to backport:

- New features. `version-15` gets fixes; the Vue onboarding wizard, for example, is v16 only.
- Changes that only make sense on Frappe 16: Python 3.14, Frappe 16 API changes, and `.github/workflows/ci.yml`, which each branch keeps for itself.

How:

1. Add `backport version-15` to the PR before merging it. When it merges, the backport bot cherry-picks its commits onto `version-15` and opens a PR titled `[Backport version-15] <original title>`. If you forgot the label, add it after merging and comment `/backport` on the PR.
2. The bot opens its PR with GitHub's built-in token, so no CI run starts on it. **Close and reopen the backport PR** to run the v15 CI, and merge it once it passes.
3. If the cherry-pick conflicts, the bot opens no PR. It comments on the original PR with the commands to finish the cherry-pick by hand; resolve the conflict, push the branch, and open the PR into `version-15` yourself.

Two cases skip `develop`:

- A fix only `version-15` needs, because the code has since changed on `develop`: branch from `version-15` and open the PR straight into it.
- An urgent fix for v16 sites while `develop` holds work that isn't ready to release: label the fix's PR `backport version-16`, merge the backport PR, then make a patch release of `version-16`.

## Releasing

`__version__` in `optima_zatca/__init__.py` is bumped on the release branch, never on `develop`. Because `develop` never touches that line, release merges never conflict on it.

`3.x.y` is the v15 line and `4.x.y` the v16 line. A release with only fixes bumps the patch (`4.1.0` → `4.1.1`); a release with any `feat` bumps the minor (`4.1.1` → `4.2.0`).

### version-16

1. Open a PR from `develop` into `version-16` titled `chore: release v4.2.0`. Merge it with **Create a merge commit**, never squash or rebase: a squashed release gives `version-16` a commit `develop` doesn't have, and the next release PR then conflicts.
2. Open a PR into `version-16` that sets `__version__ = "4.2.0"`, titled `chore(release): bump version to 4.2.0`, and merge it. The quickest way is to edit the file on GitHub with `version-16` selected and choose **Create a new branch for this commit and start a pull request**.
3. Under **Releases → Draft a new release**, create the tag `v4.2.0` on target `version-16`, pick the previous `v4` tag, click **Generate release notes**, and publish.

### version-15

1. Merge the backport PRs that make up the release.
2. Open a PR into `version-15` that sets `__version__` (for example `"3.1.1"`), titled `chore(release): bump version to 3.1.1`, and merge it.
3. Draft a release with the tag `v3.1.1` on target `version-15`, pick the previous `v3` tag, generate the notes, and publish.

## Deploying

Sites install from a release branch: `bench get-app --branch version-16 …` for ERPNext 16 and `--branch version-15 …` for ERPNext 15. Never deploy `develop`. A release branch only moves when a release is made, so update sites after a release rather than after every merge.

## Tests and CI

- CI (`.github/workflows/ci.yml`) runs on pushes and PRs to `develop` and `version-16` against Frappe 16, and to `version-15` against Frappe 15.
- On Frappe 16, `bench run-tests` writes to the site it runs on: test companies, users, custom fields, and System Settings such as the time zone. Run bench tests only on a throwaway site, never on one with real or restored data.

## When Frappe 17 ships

`develop` moves to Frappe 17 and a `version-17` branch is cut from it, with its own major version. `version-16` then becomes a maintenance branch like `version-15`, fed by `backport version-16` labels.
