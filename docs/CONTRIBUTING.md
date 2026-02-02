# Contributing Guide

Huong dan dong gop vao Kuromi Browser.

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/kurom1ii/kuromi-browser.git
cd kuromi-browser

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install with dev dependencies
pip install -e ".[dev,full]"

# Install pre-commit hooks
pre-commit install
```

## Project Structure

```
kuromi-browser/
├── kuromi_browser/          # Main package
│   ├── cdp/                 # CDP client & browser management
│   ├── dom/                 # Element locators & DOM service
│   ├── session/             # HTTP mode with TLS impersonation
│   ├── events/              # Event bus system
│   ├── watchdogs/           # Monitoring services
│   ├── llm/                 # LLM provider integrations
│   ├── agent/               # AI agent system
│   ├── stealth/             # Anti-detection & fingerprint
│   │   ├── cdp/             # CDP patches (Patchright techniques)
│   │   ├── fingerprint/     # Fingerprint generator
│   │   ├── behavior/        # Human-like actions
│   │   └── tls/             # TLS/JA3 impersonation
│   ├── actions/             # Mouse, keyboard, form controllers
│   ├── browser/             # Browser management
│   ├── network/             # Network monitoring
│   ├── waiters/             # Wait conditions
│   └── mcp/                 # Model Context Protocol server
├── tests/                   # Test suite
├── docs/                    # Documentation
└── pyproject.toml           # Project configuration
```

## Dependencies

### Core (from pyproject.toml)
| Package | Version | Purpose |
|---------|---------|---------|
| websockets | >=12.0 | CDP WebSocket connection |
| httpx | >=0.27.0 | HTTP client |
| lxml | >=5.0.0 | HTML/XML parsing |
| pydantic | >=2.0 | Data validation |
| curl_cffi | >=0.6.0 | TLS impersonation |

### Optional - LLM
| Package | Version | Purpose |
|---------|---------|---------|
| openai | >=1.0 | OpenAI API |
| anthropic | >=0.18 | Anthropic API |

### Optional - Full
| Package | Version | Purpose |
|---------|---------|---------|
| browserforge | >=1.0 | Fingerprint generation |
| Pillow | >=10.0 | Image processing |

### Dev
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0 | Testing |
| pytest-asyncio | >=0.23 | Async tests |
| ruff | >=0.3 | Linting |
| pyright | >=1.1 | Type checking |
| pre-commit | >=3.0 | Git hooks |

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run with coverage
pytest --cov=kuromi_browser

# Run verbose
pytest -v
```

### Code Quality

```bash
# Format code
ruff format .

# Lint
ruff check .

# Type check
pyright kuromi_browser

# Run all checks
pre-commit run --all-files
```

### Adding New Features

1. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Write tests first** (TDD)
   ```bash
   # Create test file
   touch tests/test_your_feature.py
   ```

3. **Implement feature**

4. **Run checks**
   ```bash
   pytest
   ruff check .
   pyright kuromi_browser
   ```

5. **Commit with clear message**
   ```bash
   git commit -m "feat: add your feature description"
   ```

6. **Create Pull Request**

## Code Style

### Python Style

- Follow PEP 8
- Use type hints
- Docstrings for public functions
- Max line length: 100 characters

```python
async def fetch_data(
    url: str,
    *,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Fetch data from URL.

    Args:
        url: Target URL
        timeout: Request timeout in seconds
        headers: Optional HTTP headers

    Returns:
        Parsed JSON response

    Raises:
        HTTPError: If request fails
    """
    ...
```

### Commit Messages

Follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance

## Testing Guidelines

### Test Structure

```python
import pytest
from kuromi_browser import YourClass

class TestYourClass:
    """Tests for YourClass."""

    def test_basic_functionality(self):
        """Test basic usage."""
        obj = YourClass()
        assert obj.method() == expected

    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async functionality."""
        obj = YourClass()
        result = await obj.async_method()
        assert result is not None
```

### Test Coverage

- Aim for 80%+ coverage
- Focus on critical paths
- Test edge cases

## Documentation

### Updating Docs

1. Edit markdown files in `docs/`
2. Update README.md for major features
3. Add examples for new APIs

### Documentation Style

- Use Vietnamese for user guides
- Use English for code comments and docstrings
- Include code examples

## Questions?

- Open an issue on GitHub
- Check existing documentation
