# Contributing to Soil Probe

## Set up

The tests run against Home Assistant 2026.11.2, the oldest version Soil Probe supports, through Home
Assistant's `pytest-homeassistant` package; it needs Python 3.14.2 or newer. With
[uv](https://docs.astral.sh/uv/):

```sh
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements_test.txt
```

Then install the [pre-commit](https://pre-commit.com/) hooks once, so each commit gets the same checks
as CI:

```sh
uvx pre-commit install
```

## Layout

`custom_components/soil_probe/`:

- `const.py`: keys and constants.
- `models.py`: the probe models and their default calibration. To add a model, add one entry to
  `MODELS` and a case to `tests/test_models.py`; the setup form's model picker is built from it.
- `config_flow.py`: adding a probe, and changing its sources under Configure. Schemas use `probatio`, Home Assistant's validation library since
  2026.11; don't import `voluptuous`.
- `translations/en.json`: edited by hand.

Tests are in `tests/`, one module per source module.

## Checks

CI runs all of these; the pre-commit hooks cover the fast ones.

```sh
.venv/bin/python -m pytest --cov=custom_components/soil_probe --cov-branch   # coverage must stay at 97% or more
uvx ruff@0.16.9 check custom_components tests scripts
uvx ruff@0.16.9 format --check custom_components tests scripts   # without --check it fixes the files
uvx codespell@2.4.3 custom_components tests scripts README.md CONTRIBUTING.md .github pyproject.toml
uvx --from actionlint-py==1.7.12.25 actionlint .github/workflows/*.yml
.venv/bin/python scripts/check_rules.py references       # no references to planning notes in the code
uv pip install --python .venv/bin/python mypy==2.3.1
.venv/bin/python -m mypy custom_components/soil_probe   # strict
docker run --rm -v "$PWD":/github/workspace ghcr.io/home-assistant/hassfest   # Home Assistant's integration validator
```

A second workflow runs the tests against the newest Home Assistant every week.

## Releases

Versions follow [Semantic Versioning](https://semver.org/): fixes raise the patch number, new features
or settings the minor number, and changes that break existing setups (a renamed entity or attribute,
a removed setting) the major number. From the first release on, a change to what a probe stores comes
with a config entry migration.

Every change is released first as a beta, a GitHub pre-release such as `v1.1.0-beta.1`. A beta
becomes a stable release once it has run for at least 48 hours on a real installation, including a
restart; the stable release may differ from its beta only in the version number, the changelog and
documentation. Changes to the documentation alone aren't released.

To release:

1. In a pull request, set `version` in `manifest.json` (without the `v`) and add a
   `## [<version>] - <date>` section to `CHANGELOG.md`.
2. After it merges, check that CI passed on that commit of `main`.
3. For a stable release, check the beta on the real installation: no Soil Probe errors or warnings in
   the log and no Soil Probe Repairs issues.
4. Tag that commit and push the tag: `git tag v<version> && git push origin v<version>`. The release
   workflow checks that the tag matches the manifest and is on `main`, then publishes the release with
   that version's changelog section, as a pre-release when the version has a suffix such as `-beta.1`.

## Commits

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
`<type>[optional scope]: <description>`, for example `fix(sensor): clamp moisture to 0–100`. The
allowed types are `feat`, `fix`, `perf`, `refactor`, `style`, `docs`, `test`, `ci`, `build`, `chore`
and `revert`. Leave out `Co-Authored-By` trailers. The `commit-msg` hook checks each message, and CI
checks every commit it's given.

Code comments explain why, not what; keep them short.
