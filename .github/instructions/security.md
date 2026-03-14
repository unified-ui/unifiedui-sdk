# Security Guidelines — unified-ui SDK (Python)

## CRITICAL: Read This First

These rules are **mandatory** for all code generation. The SDK is a library consumed by external developers — security mistakes propagate to all downstream users.

---

## 1. Input Validation

**Threat**: Malicious or malformed input flows through SDK functions into downstream systems (databases, APIs, LLMs).

### Rules

- **ALWAYS** validate and sanitize all public API inputs at the boundary (public functions, class constructors).
- **ALWAYS** use Pydantic models or explicit type checks with constraints for structured inputs.
- **ALWAYS** validate string inputs with length limits and format constraints where applicable.
- **NEVER** pass raw user input to system commands, SQL queries, or HTTP requests without validation.

### Correct Pattern

```python
from pydantic import BaseModel, Field, constr

class AgentConfig(BaseModel):
    name: constr(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9 _\-]+$")
    model: constr(min_length=1, max_length=100)
    temperature: float = Field(ge=0.0, le=2.0, default=0.7)
```

---

## 2. SSRF Prevention (Server-Side Request Forgery)

**Threat**: User-supplied URLs in SDK configuration redirect outbound requests to internal infrastructure.

### Rules

- **ALWAYS** validate URLs before making outbound HTTP requests:
  - Parse with `urllib.parse.urlparse()`
  - Verify scheme is `http` or `https`
  - Verify host is not empty
- **ALWAYS** set timeouts on all HTTP clients (30s default).
- **NEVER** blindly trust URLs from configuration — validate even internal URLs.

---

## 3. Secret & Credential Safety

### Rules

- **NEVER** hardcode secrets, API keys, or tokens in source code or tests.
- **NEVER** include real credentials in example code or documentation.
- **NEVER** log secrets — not at any log level. Mask sensitive values before logging.
- **ALWAYS** use placeholder values in examples: `"your-api-key-here"`, `"sk-..."`.
- **ALWAYS** recommend secure secret loading in docstrings (env vars, vault, etc.).

### Correct Pattern

```python
import os

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")
```

### Wrong Pattern

```python
# WRONG — hardcoded secret
api_key = "sk-abc123def456ghi789"

# WRONG — secret in log output
logger.debug(f"Using API key: {api_key}")
```

---

## 4. Prompt Injection Awareness

**Threat**: User-supplied text embedded in LLM prompts can manipulate agent behavior.

### Rules

- **ALWAYS** clearly separate system prompts from user content using distinct message roles.
- **NEVER** embed raw user input directly into system prompt strings via string interpolation.
- **ALWAYS** use the structured message format (system/user/assistant roles) provided by the SDK.
- **ALWAYS** document prompt injection risks in public API docstrings where user content is processed.

### Correct Pattern

```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_input},  # separated from system prompt
]
```

### Wrong Pattern

```python
# WRONG — user input injected into system prompt
prompt = f"You are a helpful assistant. The user says: {user_input}. Now respond."
```

---

## 5. Serialization Safety

### Rules

- **NEVER** use `pickle` for serialization/deserialization — it allows arbitrary code execution.
- **ALWAYS** use `json` for data serialization.
- **NEVER** use `yaml.load()` without `Loader=yaml.SafeLoader` — use `yaml.safe_load()`.
- **ALWAYS** validate deserialized data against expected schemas.

---

## 6. Dependency Security

### Rules

- **ALWAYS** pin dependency versions in `pyproject.toml` with minimum version bounds.
- **NEVER** add dependencies without evaluating their security track record.
- Review Dependabot alerts promptly.

---

## Quick Checklist Before Committing

- [ ] All public API inputs validated with type checks and constraints
- [ ] All outbound URLs validated (scheme, host)
- [ ] No hardcoded secrets in source or tests
- [ ] No secrets logged at any level
- [ ] User content separated from system prompts (distinct roles)
- [ ] No `pickle`, no unsafe `yaml.load()`
- [ ] HTTP clients have timeouts
- [ ] Example code uses placeholder credentials
