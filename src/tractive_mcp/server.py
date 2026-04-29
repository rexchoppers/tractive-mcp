import argparse
import getpass

from mcp.server.fastmcp import FastMCP

from tractive_mcp.client import tractive_client, save_credentials

mcp = FastMCP("tractive")


@mcp.tool()
def ping() -> str:
    """Sanity check tool — returns 'pong' so we know the server is alive."""
    return "pong"


def auth() -> None:
    """Prompt for Tractive credentials and save them."""
    print("Credentials will be saved to ~/.config/tractive-mcp/credentials.json")
    email = input("Tractive email: ")
    password = getpass.getpass("Tractive password: ")
    save_credentials(email, password)
    print("Saved.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="tractive-mcp")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("auth", help="Set up Tractive credentials")
    args = parser.parse_args()

    if args.command == "auth":
        auth()
        return

    mcp.run()

@mcp.tool()
async def whoami() -> dict:
    """Diagnostic: confirms Tractive credentials load and authenticate."""
    from tractive_mcp.client import tractive_client
    async with tractive_client() as client:
        auth = await client.authenticate()
        return {"user_id": auth.get("user_id"), "expires_at": auth.get("expires_at")}


@mcp.tool()
async def list_pets() -> list[dict]:

    """List all pets on the user's Tractive account.

    Returns each pet's id, name, pet type (dog/cat), and assigned tracker id.
    Use the pet's id when calling other tools like get_pet_location.
    """
    async with tractive_client() as client:
        objects = await client.trackable_objects()
        pets = []
        for obj in objects:
            d = await obj.details()

            print(d)

            pets.append({
                "id": d.get("_id"),
                "name": d.get("details", {}).get("name") or d.get("name"),
                "pet_type": d.get("details", {}).get("pet_type") or d.get("pet_type"),
                "tracker_id": d.get("device_id") or (d.get("device_ids") or [None])[0],
            })
        return pets

if __name__ == "__main__":
    main()