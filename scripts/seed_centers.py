from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.center_model import DiagnosticCenter
from database.session import SessionLocal
from utils.geohash import calculate_geohash

CENTERS = (
    (
        "Demo Diagnostics - Connaught Place",
        "A-12, Connaught Place, New Delhi, Delhi",
        28.6315,
        77.2167,
    ),
    (
        "Demo Diagnostics - Gurugram",
        "Sector 29, Gurugram, Haryana",
        28.4595,
        77.0266,
    ),
    (
        "Demo Diagnostics - Noida",
        "Sector 18, Noida, Uttar Pradesh",
        28.5708,
        77.3261,
    ),
)


def seed_centers(session: Session) -> tuple[int, int]:
    names = [center[0] for center in CENTERS]
    existing_names = set(
        session.scalars(
            select(DiagnosticCenter.name).where(DiagnosticCenter.name.in_(names))
        ).all()
    )
    new_centers = [
        DiagnosticCenter(
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            geohash=calculate_geohash(latitude, longitude),
        )
        for name, address, latitude, longitude in CENTERS
        if name not in existing_names
    ]
    session.add_all(new_centers)
    return len(new_centers), len(CENTERS) - len(new_centers)


def main() -> None:
    with SessionLocal.begin() as session:
        inserted, skipped = seed_centers(session)

    print(f"Centers seeded: {inserted} inserted, {skipped} already existed.")


if __name__ == "__main__":
    main()
