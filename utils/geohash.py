import math

import geohash2


EARTH_RADIUS_KM = 6371.0088
STORED_GEOHASH_PRECISION = 8
MAX_GEOHASH_COVER_CELLS = 256


def calculate_geohash(latitude: float, longitude: float) -> str:
    return geohash2.encode(
        latitude,
        longitude,
        precision=STORED_GEOHASH_PRECISION,
    )


def geohashes_for_radius(
    latitude: float,
    longitude: float,
    radius_km: float,
) -> list[str]:
    angular_radius = min(radius_km / EARTH_RADIUS_KM, math.pi)
    latitude_radians = math.radians(latitude)
    latitude_min = max(-math.pi / 2, latitude_radians - angular_radius)
    latitude_max = min(math.pi / 2, latitude_radians + angular_radius)

    if (
        angular_radius >= math.pi / 2 - abs(latitude_radians)
        or angular_radius >= math.pi
    ):
        longitude_intervals = [(-180.0, 180.0)]
    else:
        longitude_delta = math.degrees(
            math.asin(
                math.sin(angular_radius) / math.cos(latitude_radians)
            )
        )
        longitude_min = longitude - longitude_delta
        longitude_max = longitude + longitude_delta

        if longitude_min < -180:
            longitude_intervals = [
                (-180.0, longitude_max),
                (longitude_min + 360, 180.0),
            ]
        elif longitude_max > 180:
            longitude_intervals = [
                (longitude_min, 180.0),
                (-180.0, longitude_max - 360),
            ]
        else:
            longitude_intervals = [(longitude_min, longitude_max)]

    for precision in range(STORED_GEOHASH_PRECISION, 0, -1):
        _, _, latitude_error, longitude_error = geohash2.decode_exactly(
            geohash2.encode(latitude, longitude, precision=precision)
        )
        cell_height = latitude_error * 2
        cell_width = longitude_error * 2
        row_count = round(180 / cell_height)
        column_count = round(360 / cell_width)

        first_row = max(
            0,
            math.floor((math.degrees(latitude_min) + 90) / cell_height) - 1,
        )
        last_row = min(
            row_count - 1,
            math.floor((math.degrees(latitude_max) + 90) / cell_height) + 1,
        )
        rows = range(first_row, last_row + 1)

        columns = set()
        for interval_min, interval_max in longitude_intervals:
            first_column = max(
                0,
                math.floor((interval_min + 180) / cell_width) - 1,
            )
            last_column = min(
                column_count - 1,
                math.floor((interval_max + 180) / cell_width) + 1,
            )
            columns.update(range(first_column, last_column + 1))

        if len(rows) * len(columns) <= MAX_GEOHASH_COVER_CELLS:
            return [
                geohash2.encode(
                    -90 + (row + 0.5) * cell_height,
                    -180 + (column + 0.5) * cell_width,
                    precision=precision,
                )
                for row in rows
                for column in sorted(columns)
            ]

    return []


def distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    latitude_a_radians = math.radians(latitude_a)
    latitude_b_radians = math.radians(latitude_b)
    latitude_delta = latitude_b_radians - latitude_a_radians
    longitude_delta = math.radians(longitude_b - longitude_a)

    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_a_radians)
        * math.cos(latitude_b_radians)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, haversine)))
