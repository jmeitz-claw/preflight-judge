# Releasing preflight-judge (free)

MIT-licensed and free forever. This is how to *publish* it so people can install it.

## TL;DR
1. Push this code to a **public** GitHub repo (`preflight-judge`).
2. Free account on [PyPI](https://pypi.org) (and [TestPyPI](https://test.pypi.org) to rehearse).
3. Set up **Trusted Publishing** (below) — then cutting a GitHub Release auto-publishes to PyPI, tokenless.

Once on PyPI: `pip install preflight-judge`.

## One-time: PyPI Trusted Publishing (recommended)
1. PyPI → **Your projects → Publishing → Add a pending publisher**:
   - PyPI Project Name: `preflight-judge`
   - Owner: `jmeitz-claw`
   - Repository name: `preflight-judge`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
2. GitHub repo → **Settings → Environments → New environment** → name it `pypi`.

The included `.github/workflows/publish.yml` does the rest.

## Cutting a release
```bash
# bump version in pyproject.toml and preflight/__init__.py (__version__)
git tag v0.1.0
git push origin v0.1.0
# GitHub → Releases → Draft a new release → pick tag → Publish
```
Publishing the Release triggers `publish.yml`, which builds + uploads to PyPI.

## Manual fallback (API token)
```bash
python -m pip install build twine
python -m build
python -m twine upload dist/*        # paste a PyPI API token
```

## Versioning
SemVer. Bump the version in **two** places kept in sync: `pyproject.toml` and
`preflight/__init__.py` (`__version__`).
