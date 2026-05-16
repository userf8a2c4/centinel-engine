# Contributing to Centinel Engine

**ES: Contribuyendo a Centinel Engine**

## Welcome Contributors

Centinel Engine is open-source under AGPL-3.0. We welcome technical contributions, bug reports, audits, and operational feedback.

**ES: Centinel Engine es open-source bajo AGPL-3.0. Damos la bienvenida a contribuciones técnicas, reportes de bugs, auditorías y feedback operativo.**

---

## How to Contribute

### 1. Report Issues

Found a bug or security issue? Open an issue on GitHub with:
- Clear description of problem
- Steps to reproduce
- Expected vs. actual behavior
- Platform/environment info

**Security issues:** Email instead of public issue (see [SECURITY_AUDIT.md](SECURITY_AUDIT.md))

### 2. Submit Code

1. Fork the repo
2. Create feature branch: `git checkout -b feature/your-feature`
3. Write tests for new functionality
4. Ensure all tests pass: `poetry run pytest -q`
5. Commit with clear message (include issue #)
6. Submit PR with description

### 3. Improve Documentation

Docs are in `docs/` (Markdown) and code comments (Python). Improvements welcome:
- Clarify operational procedures
- Add examples or use cases
- Translate to Spanish/English
- Fix typos

### 4. Audit & Security Review

We welcome security audits and threat modeling. Contact the maintainer with:
- Audit findings (structured report preferred)
- Severity assessment
- Suggested mitigations
- Timeline for disclosure

---

## Work-In-Progress Areas

### Dashboard (Future)

The Streamlit dashboard is **work-in-progress** and currently archived (`.archive/dashboard-wip/`).

**What it was intended to do:**
- Operator UI for witness management
- Real-time alert display
- Snapshot history browsing
- Report generation

**Why archived:**
- Not critical path (public verification is via web verifier)
- Would require React migration (pending design)
- Priority is core operational tools first

**How to contribute:**
If you want to finish the dashboard:
1. Open an issue describing your approach
2. Discuss with maintainer
3. Fork and develop on your branch
4. Test against demo data
5. Submit PR with clean separation from core

---

## Code Standards

- **Python 3.10+**: Use type hints, f-strings, dataclasses
- **Tests:** Comprehensive test suite in `tests/` — add tests for new code
- **Docs:** Docstrings in English (class/function level) and comment key logic
- **Security:** Avoid secrets in code; use `config/secrets/` pattern
- **Formatting:** Follow existing style; `flake8` config in `.flake8`

### Test Coverage

Run tests:
```bash
poetry run pytest tests/ -v
```

Core tests (custody, hashing, transparency) must pass. Peripheral tests (API, chaos) may be skipped if environment incomplete.

---

## Development Setup

```bash
git clone https://github.com/userf8a2c4/centinel-engine.git
cd centinel-engine
poetry install
poetry run pytest -q
```

For local deployment with test data:
```bash
make init
make pipeline
```

---

## Licensing & Attribution

By contributing, you agree that your work is licensed under AGPL-3.0.

- Small fixes (typos, docs): No attribution required
- Substantial features: Mention in commit message or CONTRIBUTORS list (future)
- Translations: Credit your name in the file header

---

## Code of Conduct

This project is politically neutral and committed to inclusive collaboration. We expect:
- Respectful, professional communication
- No partisan or discriminatory language
- Focus on technical merit and electoral integrity
- Good faith problem-solving

Violations can be reported to the maintainer.

---

## Questions?

- Open a GitHub discussion or issue
- Check `docs/` for architecture and operational guides
- Review existing code for patterns

Thank you for supporting electoral integrity through open technical auditing!

---

**Maintained by:** userf8a2c4  
**License:** GNU AGPL-3.0  
**Last Updated:** May 2026
