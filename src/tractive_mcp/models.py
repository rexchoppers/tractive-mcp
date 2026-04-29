from dataclasses import dataclass, asdict, field
from typing import Optional


@dataclass
class PetResponse:
    id: Optional[str]
    name: Optional[str]
    pet_type: Optional[str]
    device_id: Optional[str]

    @classmethod
    def from_raw(cls, d: dict) -> "PetResponse":
        return cls(
            id=d.get("_id"),
            name=d.get("details", {}).get("name") or d.get("name"),
            pet_type=d.get("details", {}).get("pet_type") or d.get("pet_type"),
            device_id=d.get("device_id") or (d.get("device_ids") or [None])[0],
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PetLocationResponse:
    latitude: Optional[float]
    longitude: Optional[float]
    speed: Optional[float]
    altitude: Optional[float]
    course: Optional[float]
    accuracy: Optional[float]
    sensor_used: Optional[str]
    time: Optional[int]
    time_rcvd: Optional[int]

    @classmethod
    def from_raw(cls, pos: dict) -> "PetLocationResponse":
        latlong = pos.get("latlong", [None, None])
        return cls(
            latitude=latlong[0],
            longitude=latlong[1],
            speed=pos.get("speed"),
            altitude=pos.get("altitude"),
            course=pos.get("course"),
            accuracy=pos.get("pos_uncertainty"),
            sensor_used=pos.get("sensor_used"),
            time=pos.get("time"),
            time_rcvd=pos.get("time_rcvd"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Coordinates:
    latitude: float
    longitude: float


@dataclass
class PetDistanceResponse:
    distance_metres: float
    home: Coordinates
    current: Coordinates

    @classmethod
    def from_raw(cls, distance: float, home: list, current: list) -> "PetDistanceResponse":
        return cls(
            distance_metres=round(distance, 1),
            home=Coordinates(latitude=home[0], longitude=home[1]),
            current=Coordinates(latitude=current[0], longitude=current[1]),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrackerStatusResponse:
    device_id: str
    state: Optional[str]
    battery_level: Optional[int]
    charging_state: Optional[str]
    connection_state: Optional[str]
    firmware_version: Optional[str]
    hardware_revision: Optional[str]
    model_number: Optional[str]

    @classmethod
    def from_raw(cls, device_id: str, details: dict, hw: dict) -> "TrackerStatusResponse":
        return cls(
            device_id=device_id,
            state=details.get("state"),
            battery_level=hw.get("battery_level"),
            charging_state=details.get("charging_state"),
            connection_state=details.get("connection_state"),
            firmware_version=hw.get("fw_version"),
            hardware_revision=hw.get("hw_revision"),
            model_number=details.get("model_number"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BoundingBox:
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


@dataclass
class PositionPoint:
    latitude: float
    longitude: float
    time: Optional[int]
    speed: Optional[float]
    accuracy: Optional[float]
    sensor_used: Optional[str]


@dataclass
class RecentPositionsSummary:
    point_count: int
    total_distance_metres: float
    time_from: Optional[int]
    time_to: Optional[int]
    bounding_box: BoundingBox


@dataclass
class RecentPositionsResponse:
    summary: RecentPositionsSummary
    points: Optional[list[dict]] = field(default=None)

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.points is None:
            del d["points"]
        return d
