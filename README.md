# tractive-mcp

An MCP server for the [Tractive](https://tractive.com) GPS pet tracker. Lets AI assistants like Claude query your pet's location, tracker status, position history, and more.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- A Tractive account with at least one GPS tracker

## Quick Start (from PyPI)

```bash
# Authenticate
uvx tractive-mcp auth

# Add to Claude Code
claude mcp add tractive -- uvx tractive-mcp
```

## Install from Source

```bash
git clone https://github.com/rexchoppers/tractive-mcp.git
cd tractive-mcp
uv sync
uv run tractive-mcp auth
claude mcp add tractive -- uv run tractive-mcp
```

## Authentication

Tractive does not provide any OAuth mechanisms. As a result, email and passwords have to be stored locally. Run the auth command to save your Tractive credentials:

```bash
uvx tractive-mcp auth
```

Credentials are stored at `~/.config/tractive-mcp/credentials.json` with `0600` permissions.

## Usage with Claude Code

```bash
claude mcp add tractive -- uvx tractive-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "tractive": {
      "command": "uvx",
      "args": ["tractive-mcp"]
    }
  }
}
```

## Available Tools

### Discovery
| Tool | Description |
|------|-------------|
| `list_pets` | Lists all pets on the account with their name, type, and device_id |

### Location
| Tool | Description |
|------|-------------|
| `get_pet_location(device_id)` | Current GPS coordinates, speed, altitude, accuracy |
| `get_pet_distance_from_home(device_id)` | Distance in metres from the pet's home location |
| `get_recent_positions(device_id, hours, include_points)` | Position history with summary stats (distance, bounding box, point count). Set `include_points=True` for the full breadcrumb trail |

### Tracker
| Tool | Description |
|------|-------------|
| `get_tracker_status(device_id)` | Battery level, charging state, connection state, firmware |
| `set_buzzer(device_id, active)` | Turn the tracker buzzer on/off |
| `set_led(device_id, active)` | Turn the tracker LED on/off |
| `set_live_tracking(device_id, active)` | Toggle live tracking mode (more frequent GPS, more battery) |

### Pet Info
| Tool | Description |
|------|-------------|
| `get_pet_profile(device_id)` | Full pet profile — breed, weight, birthday, activity goals |

### Emergency
| Tool | Description |
|------|-------------|
| `lost_pet(device_id, enable_live_tracking, enable_buzzer, enable_led)` | All-in-one emergency tool. Returns location, distance from home, tracker status, and recent activity. Optionally activates live tracking, buzzer, and LED |

## Project Structure

```
src/tractive_mcp/
  server.py    — MCP server, tool definitions, auth CLI
  client.py    — Credential management, Tractive client helper
  models.py    — Response dataclasses
```

## License

See [LICENSE](LICENSE).
