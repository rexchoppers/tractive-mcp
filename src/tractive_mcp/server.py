from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tractive")

@mcp.tool()
def ping() -> str:
    """Sanity check tool — returns 'pong' so we know the server is alive."""
    return "pong"

def main() -> None:
    mcp.run()

if __name__ == "__main__":
    main()