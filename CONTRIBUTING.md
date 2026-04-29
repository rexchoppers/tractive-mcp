# Contributing

## Getting Started

```bash
git clone https://github.com/rexchoppers/tractive-mcp.git
cd tractive-mcp
make sync
make auth
```

## Development

Run the server locally:

```bash
make dev
```

Test tools interactively with the MCP inspector:

```bash
make inspect
```

## Adding a New Tool

1. Add a response dataclass to `src/tractive_mcp/models.py` if the tool returns structured data.
2. Add the tool function to `src/tractive_mcp/server.py` with the `@mcp.tool()` decorator.
3. Use `async with tractive_client() as client:` to get an authenticated client.
4. Use `device_id` as the parameter name for tracker identification (not `tracker_id` or `pet_id`).
5. Update the tools table in `README.md`.

## Conventions

- All tracker-related tools use `device_id` as their identifier, matching the output of `list_pets`.
- Response shaping is done via dataclasses in `models.py` — each has a `from_raw()` classmethod and `to_dict()` method.
- Every tool opens its own client session via the `tractive_client()` context manager.

## Pull Requests

- Keep PRs focused — one feature or fix per PR.
- Update the README if you add or change a tool.
- Bump the version in `pyproject.toml` for any user-facing changes.

## Reporting Issues

Open an issue at https://github.com/rexchoppers/tractive-mcp/issues with:

- What you expected to happen
- What actually happened
- Steps to reproduce
