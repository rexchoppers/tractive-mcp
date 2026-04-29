import argparse
import getpass
import time as _time

from mcp.server.fastmcp import FastMCP

from tractive_mcp.client import haversine, tractive_client, save_credentials
from tractive_mcp.models import (
    PetResponse, PetLocationResponse, PetDistanceResponse,
    TrackerStatusResponse, RecentPositionsResponse, RecentPositionsSummary,
    BoundingBox, PositionPoint,
)

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
            pets.append(PetResponse.from_raw(d).to_dict())
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
        return PetLocationResponse.from_raw(pos).to_dict()

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
        return PetDistanceResponse.from_raw(distance, home, latlong).to_dict()


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
        return TrackerStatusResponse.from_raw(device_id, details, hw).to_dict()


@mcp.tool()
async def get_recent_positions(
    device_id: str, hours: int = 24, include_points: bool = False
) -> dict:
    """Get recent position history (breadcrumb trail) for a pet.

    Args:
        device_id: The device_id from list_pets.
        hours: How many hours of history to fetch (default 24).
        include_points: If True, include the full list of position points.
            Set to False (default) to save context when you only need stats.

    Returns a summary with point count, total distance, time range,
    and bounding box. If include_points is True, also returns the points array.
    """
    now = _time.time()
    time_from = now - (hours * 3600)

    async with tractive_client() as client:
        tracker = client.tracker(device_id)
        raw = await tracker.positions(time_from, now, "json_segments")

    # raw is a list of segments, each segment is a list of position dicts
    flat: list[dict] = []
    for segment in raw if isinstance(raw, list) else []:
        entries = segment if isinstance(segment, list) else [segment]
        for entry in entries:
            ll = entry.get("latlong", [None, None])
            flat.append({
                "latitude": ll[0],
                "longitude": ll[1],
                "time": entry.get("time"),
                "speed": entry.get("speed"),
                "accuracy": entry.get("pos_uncertainty"),
                "sensor_used": entry.get("sensor_used"),
            })

    # Compute summary
    total_distance = 0.0
    for i in range(1, len(flat)):
        prev, curr = flat[i - 1], flat[i]
        if prev["latitude"] and curr["latitude"]:
            total_distance += haversine(
                prev["latitude"], prev["longitude"],
                curr["latitude"], curr["longitude"],
            )

    lats = [p["latitude"] for p in flat if p["latitude"] is not None]
    lons = [p["longitude"] for p in flat if p["longitude"] is not None]
    times = [p["time"] for p in flat if p["time"] is not None]

    summary = RecentPositionsSummary(
        point_count=len(flat),
        total_distance_metres=round(total_distance, 1),
        time_from=min(times) if times else None,
        time_to=max(times) if times else None,
        bounding_box=BoundingBox(
            min_lat=min(lats) if lats else 0,
            max_lat=max(lats) if lats else 0,
            min_lon=min(lons) if lons else 0,
            max_lon=max(lons) if lons else 0,
        ),
    )

    resp = RecentPositionsResponse(
        summary=summary,
        points=flat if include_points else None,
    )
    return resp.to_dict()


if __name__ == "__main__":
    main()