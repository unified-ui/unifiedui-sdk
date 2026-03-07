# Contributing to unified-ui SDK

Thank you for your interest in contributing! 🎉

## Development Setup

```bash
# Clone the repository
git clone https://github.com/unified-ui/unifiedui-sdk.git
cd unifiedui-sdk

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg
```

## Development Workflow

1. **Fork** the repository
2. **Create a branch** following the naming convention: `<type>/<description>`
   - Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
   - Example: `feat/add-langchain-tracing`
3. **Make your changes** and write tests
4. **Run quality checks** locally:
   ```bash
   ruff check .              # Lint
   ruff format .             # Format
   mypy src/unifiedui_sdk/   # Type check
   pytest tests/ -n auto --cov=unifiedui_sdk --cov-fail-under=80  # Tests + coverage
   ```
5. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat(tracing): add LangChain callback handler
   fix(streaming): handle empty response chunks
   ```
6. **Push** and open a Pull Request

## Code Standards

- **Type hints** on all public functions and methods
- **Docstrings** in Google style on all public APIs
- **Test coverage** must stay above **80%**
- **Ruff** must pass with zero warnings
- Mark the package as typed (`py.typed`)

## Reporting Issues

- Use GitHub Issues
- Include: Python version, SDK version, steps to reproduce, expected vs. actual behavior

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
