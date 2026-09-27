from datetime import datetime, timezone, timedelta, time

IST = timezone(timedelta(hours=5, minutes=30))

var = datetime.combine(
    datetime.strptime("2026-09-27", "%Y-%m-%d").date(),
    time(16, 0, 0),
    tzinfo=IST,
).astimezone(timezone.utc)

print(var)
