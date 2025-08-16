---
applyTo: '*.py'
---
# Python Style

- Python 3.13+
- Use modern syntax and full type annotations
- Ruff formatter may remove unused imports on save, so when adding code that needs new imports, first add the code, then the imports.
- Use | instead of `Union`
- Use builtins like `list`, `dict` instead of importing `List` and `Dict` from `typing`
- Use | None instead of `Optional`
- Note that `Any` would still need to be imported from `typing`, because `any` is a built-in function
- Always type optional keyword arguments correctly e.g. `def f(x: int | None = None)`
- Use `Literal` types for function parameters with well-defined options (e.g. `direction: Literal[1, 0, -1]` instead of `direction: int`)
- Stop and ask me before using something like `# type: ignore` or `# noqa` to fix a type error
- Stop and ask me before using `cast` to fix a type error
- When calling functions, use the keywords whenever you can. So instead of `sum = add(3, 7)`, I want `sum = add(a=3, b=7)`
- Use `pathlib` instead of `os.path`
- Use `httpx` instead of `requests`
- Use `loguru` for logging
- Not a hard rule but prefer functional programming over object oriented programming
