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


@mcp.tool()
async def lost_pet(
    device_id: str,
    enable_live_tracking: bool = True,
    enable_buzzer: bool = False,
    enable_led: bool = False,
) -> dict:
    """Emergency tool — call when a pet is lost or missing.

    Gathers all critical info in one call: current location, distance from home,
    tracker battery/connection status, and recent movement summary.
    Can activate live tracking, buzzer, and LED on the tracker.

    Args:
        device_id: The device_id from list_pets.
        enable_live_tracking: Turn on live tracking for frequent GPS updates (default True).
        enable_buzzer: Turn on the tracker buzzer to help locate the pet nearby (default False).
        enable_led: Turn on the tracker LED light (default False).
    """
    async with tractive_client() as client:
        tracker = client.tracker(device_id)

        # Fetch everything we need in parallel
        pos = await tracker.pos_report()
        details = await tracker.details()
        hw = await tracker.hw_info()

        # Find home location from the pet object
        home = None
        objects = await client.trackable_objects()
        pet_name = None
        for obj in objects:
            d = await obj.details()
            obj_device = d.get("device_id") or (d.get("device_ids") or [None])[0]
            if obj_device == device_id:
                home = d.get("home_location")
                pet_name = d.get("details", {}).get("name") or d.get("name")
                break

        # Current position
        latlong = pos.get("latlong", [None, None])

        # Distance from home
        distance_from_home = None
        if home and latlong[0] is not None:
            distance_from_home = round(haversine(home[0], home[1], latlong[0], latlong[1]), 1)

        # Recent positions summary (last 3 hours)
        now = _time.time()
        raw = await tracker.positions(now - 10800, now, "json_segments")
        recent_points = 0
        for segment in raw if isinstance(raw, list) else []:
            entries = segment if isinstance(segment, list) else [segment]
            recent_points += len(entries)

        # Activate tracker features as requested
        if enable_live_tracking:
            await tracker.set_live_tracking_active(True)
        if enable_buzzer:
            await tracker.set_buzzer_active(True)
        if enable_led:
            await tracker.set_led_active(True)

        return {
            "pet_name": pet_name,
            "current_location": {
                "latitude": latlong[0],
                "longitude": latlong[1],
                "accuracy_metres": pos.get("pos_uncertainty"),
                "sensor": pos.get("sensor_used"),
                "last_fix_time": pos.get("time"),
            },
            "distance_from_home_metres": distance_from_home,
            "home_location": {"latitude": home[0], "longitude": home[1]} if home else None,
            "tracker": {
                "battery_level": hw.get("battery_level"),
                "state": details.get("state"),
                "charging_state": details.get("charging_state"),
                "connection_state": details.get("connection_state"),
            },
            "recent_activity": {
                "points_last_3_hours": recent_points,
            },
            "actions_taken": {
                "live_tracking": enable_live_tracking,
                "buzzer": enable_buzzer,
                "led": enable_led,
            },
        }


@mcp.tool()
async def set_buzzer(device_id: str, active: bool) -> dict:
    """Turn the tracker buzzer on or off.

    Args:
        device_id: The device_id from list_pets.
        active: True to turn on, False to turn off.
    """
    async with tractive_client() as client:
        tracker = client.tracker(device_id)
        await tracker.set_buzzer_active(active)
        return {"buzzer": "on" if active else "off"}


@mcp.tool()
async def set_led(device_id: str, active: bool) -> dict:
    """Turn the tracker LED light on or off.

    Args:
        device_id: The device_id from list_pets.
        active: True to turn on, False to turn off.
    """
    async with tractive_client() as client:
        tracker = client.tracker(device_id)
        await tracker.set_led_active(active)
        return {"led": "on" if active else "off"}


@mcp.tool()
async def set_live_tracking(device_id: str, active: bool) -> dict:
    """Turn live tracking mode on or off. Live tracking gives more frequent GPS updates but uses more battery.

    Args:
        device_id: The device_id from list_pets.
        active: True to turn on, False to turn off.
    """
    async with tractive_client() as client:
        tracker = client.tracker(device_id)
        await tracker.set_live_tracking_active(active)
        return {"live_tracking": "on" if active else "off"}


@mcp.tool()
async def get_pet_profile(device_id: str) -> dict:
    """Get the full profile of a pet including breed, weight, birthday, and activity goals.

    Args:
        device_id: The device_id from list_pets.
    """
    async with tractive_client() as client:
        objects = await client.trackable_objects()
        for obj in objects:
            d = await obj.details()
            obj_device = d.get("device_id") or (d.get("device_ids") or [None])[0]
            if obj_device == device_id:
                details = d.get("details", {})
                activity = details.get("activity_settings", {})
                return {
                    "name": details.get("name"),
                    "pet_type": details.get("pet_type"),
                    "breed_ids": details.get("breed_ids"),
                    "gender": details.get("gender"),
                    "birthday": details.get("birthday"),
                    "weight_grams": details.get("weight"),
                    "height_metres": details.get("height"),
                    "neutered": details.get("neutered"),
                    "chip_id": details.get("chip_id") or None,
                    "home_location": d.get("home_location"),
                    "created_at": d.get("created_at"),
                    "activity_goals": {
                        "daily_goal": activity.get("daily_goal"),
                        "daily_distance_goal": activity.get("daily_distance_goal"),
                        "daily_active_minutes_goal": activity.get("daily_active_minutes_goal"),
                    },
                }
        return {"error": f"No pet found with device_id {device_id}"}


if __name__ == "__main__":
    main()