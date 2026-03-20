# Contributing to TACO

Thank you for your interest in contributing to The A2A Construction Open-standard.

## Developer Setup

**Prerequisites:** Python 3.10+

```bash
git clone https://github.com/pelles-ai/taco.git && cd taco
make install    # pip install -e sdk[dev]
make test       # verify everything works
```

## Development Commands

| Command | Description |
|---------|-------------|
| `make install` | Install SDK with dev dependencies |
| `make lint` | Run ruff linter |
| `make format` | Run ruff formatter |
| `make typecheck` | Run mypy type checker |
| `make test` | Run tests |
| `make test-verbose` | Run tests with verbose output |
| `make check-all` | Run all checks (mirrors CI exactly) |
| `make clean` | Remove caches and build artifacts |

## Testing

- Tests live in `sdk/tests/`, one file per module
- Run a specific test: `cd sdk && pytest tests/test_server.py -v`
- Run a specific test function: `cd sdk && pytest tests/test_server.py::test_name -v`
- Uses `asyncio_mode = "auto"` — no need for `@pytest.mark.asyncio`

## Code Style

- **Linter/formatter**: ruff (line-length 100, target Python 3.10)
- **Type checker**: mypy with `pydantic.mypy` plugin
- **Import convention**: Use `from taco.types import ...`, never `from a2a.types` directly
- **Helpers**: Use `taco._compat` helpers (`make_text_part`, `make_data_part`, etc.)

## Commit Message Format

Format: `<scope>: <imperative verb> <what>`

| Scope | When |
|-------|------|
| `sdk` | SDK source changes |
| `ui` | Website or monitor UI |
| `docs` | Documentation |
| `ci` | CI/CD workflows |
| `examples` | Demo and examples |
| `spec` | Protocol specification |

Examples:
- `sdk: add streaming support to TacoClient`
- `docs: update agent card extension spec`
- `ci: add Python 3.12 to test matrix`

## PR Checklist

- [ ] `make check-all` passes
- [ ] Tests added for new functionality
- [ ] All imports use `taco.types` / `taco._compat`
- [ ] CHANGELOG.md updated if user-facing

---

## How to Contribute

### Feedback & Discussion
- Open a **GitHub Discussion** for questions, ideas, or general feedback
- Open an **Issue** for bugs, schema problems, or specific improvement proposals

### Schema Contributions
If you'd like to propose a new data schema or modify an existing one:
1. Open an issue describing the use case
2. Fork the repo and add/modify the schema in `spec/schemas/`
3. Include example payloads
4. Submit a pull request

### Task Type Proposals
New task types should be proposed via issue first, with:
- A clear name and description
- Which project phase it belongs to (preconstruction, document management, field/coordination)
- Input and output schema references
- At least one real-world use case

### SDK Contributions
- Follow existing code style
- Include tests for new functionality
- Update documentation as needed

## Code of Conduct

Be constructive, respectful, and focused on making the standard better for the industry. We're building something together.

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
