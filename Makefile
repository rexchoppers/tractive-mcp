.PHONY: sync build publish auth dev inspect clean

sync:
	uv sync

build:
	uv build

publish: build
	uv publish

auth:
	uv run tractive-mcp auth

dev:
	uv run tractive-mcp

inspect:
	uv run mcp dev src/tractive_mcp/server.py

clean:
	rm -rf dist/ *.egg-info
