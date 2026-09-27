from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.test_model import DiagnosticTest
from database.session import SessionLocal

TESTS = (
    (
        "Complete Blood Count (CBC)",
        "A blood test that measures red blood cells, white blood cells, and platelets.",
    ),
    (
        "Comprehensive Metabolic Panel",
        "A blood test that measures key substances related to metabolism, kidney, and liver function.",
    ),
    (
        "Lipid Profile",
        "A blood test that measures cholesterol and triglyceride levels.",
    ),
    (
        "Thyroid Profile (TSH)",
        "A blood test that measures thyroid-stimulating hormone levels.",
    ),
    (
        "HbA1c",
        "A blood test that estimates average blood glucose over approximately three months.",
    ),
)


def seed_tests(session: Session) -> tuple[int, int]:
    names = [test[0] for test in TESTS]
    existing_names = set(
        session.scalars(
            select(DiagnosticTest.name).where(DiagnosticTest.name.in_(names))
        ).all()
    )
    new_tests = [
        DiagnosticTest(
            name=name,
            description=description,
            image_url=None,
            is_global=True,
        )
        for name, description in TESTS
        if name not in existing_names
    ]
    session.add_all(new_tests)
    return len(new_tests), len(TESTS) - len(new_tests)


def main() -> None:
    with SessionLocal.begin() as session:
        inserted, skipped = seed_tests(session)

    print(f"Diagnostic tests seeded: {inserted} inserted, {skipped} already existed.")


if __name__ == "__main__":
    main()
