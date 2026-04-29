import argparse
import getpass

from mcp.server.fastmcp import FastMCP

from tractive_mcp.client import haversine, tractive_client, save_credentials

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

            pets.append({
                "id": d.get("_id"),
                "name": d.get("details", {}).get("name") or d.get("name"),
                "pet_type": d.get("details", {}).get("pet_type") or d.get("pet_type"),
                "device_id": d.get("device_id") or (d.get("device_ids") or [None])[0],
            })
        return pets

@mcp.tool()
async def get_pet_location(device_id: str) -> dict:
    """Get the current GPS location of a pet.

    Args:
        device_id: The device_id from list_pets.

    Returns lat, lon, speed, altitude, time, and other position data.
    """
    async with tractive_client() as client:
        tracker = client.tracker(device_id)
        pos = await tracker.pos_report()
        return {
            "latitude": pos.get("latlong", [None, None])[0],
            "longitude": pos.get("latlong", [None, None])[1],
            "speed": pos.get("speed"),
            "altitude": pos.get("altitude"),
            "course": pos.get("course"),
            "accuracy": pos.get("pos_uncertainty"),
            "sensor_used": pos.get("sensor_used"),
            "time": pos.get("time"),
            "time_rcvd": pos.get("time_rcvd"),
        }

@mcp.tool()
async def get_pet_distance_from_home(device_id: str) -> dict:
    """Get how far a pet currently is from its home location.

    Args:
        device_id: The device_id from list_pets.

    Returns distance in metres, plus the home and current coordinates.
    """
    async with tractive_client() as client:
        # Find the pet that owns this device to get home_location
        objects = await client.trackable_objects()
        home = None
        for obj in objects:
            d = await obj.details()
            obj_device = d.get("device_id") or (d.get("device_ids") or [None])[0]
            if obj_device == device_id:
                home = d.get("home_location")
                break

        if not home:
            return {"error": "No home_location found for this device."}

        tracker = client.tracker(device_id)
        pos = await tracker.pos_report()
        latlong = pos.get("latlong", [None, None])

        distance = haversine(home[0], home[1], latlong[0], latlong[1])

        return {
            "distance_metres": round(distance, 1),
            "home": {"latitude": home[0], "longitude": home[1]},
            "current": {"latitude": latlong[0], "longitude": latlong[1]},
        }


@mcp.tool()
async def get_tracker_status(device_id: str) -> dict:
    """Get the status of a Tractive GPS tracker.

    Args:
        device_id: The device_id from list_pets.

    Returns battery level, charging state, connection state, and hardware info.
    """
    async with tractive_client() as client:
        tracker = client.tracker(device_id)
        details, hw = await tracker.details(), await tracker.hw_info()
        return {
            "device_id": device_id,
            "state": details.get("state"),
            "battery_level": hw.get("battery_level"),
            "charging_state": details.get("charging_state"),
            "connection_state": details.get("connection_state"),
            "firmware_version": hw.get("fw_version"),
            "hardware_revision": hw.get("hw_revision"),
            "model_number": details.get("model_number"),
        }


if __name__ == "__main__":
    main()