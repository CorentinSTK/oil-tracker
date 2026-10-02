"""Catalyst calendar.

Rule-based schedule of the recurring releases that move oil. EIA weekly and
CFTC/Baker Hughes follow fixed weekday rules (with US-holiday shifts); the
monthly agency reports follow typical patterns and are flagged "est." -
always confirm on the publisher's own calendar (links included).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from pandas.tseries.holiday import USFederalHolidayCalendar

ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Event:
    when: datetime          # timezone-aware, ET
    name: str
    source: str
    url: str
    estimated: bool = False
    note: str = ""


def _holidays(start: date, end: date) -> set[date]:
    return {d.date() for d in USFederalHolidayCalendar().holidays(start, end)}


def eia_wpsr_dates(start: date, end: date) -> list[datetime]:
    """EIA Weekly Petroleum Status Report: Wednesday 10:30 ET; if a federal
    holiday falls Monday-Wednesday of that week it slips to Thursday 11:00 ET."""
    hol = _holidays(start - timedelta(days=7), end + timedelta(days=7))
    out = []
    d = start + timedelta(days=(2 - start.weekday()) % 7)  # next Wednesday
    while d <= end:
        monday = d - timedelta(days=2)
        if any(monday + timedelta(days=i) in hol for i in range(3)):
            out.append(datetime.combine(d + timedelta(days=1), time(11, 0), ET))
        else:
            out.append(datetime.combine(d, time(10, 30), ET))
        d += timedelta(days=7)
    return out


def _weekly(start: date, end: date, weekday: int, at: time) -> list[datetime]:
    hol = _holidays(start, end + timedelta(days=7))
    d = start + timedelta(days=(weekday - start.weekday()) % 7)
    out = []
    while d <= end:
        day = d
        while day in hol:  # holiday Friday -> previous business day
            day -= timedelta(days=1)
        out.append(datetime.combine(day, at, ET))
        d += timedelta(days=7)
    return out


def _nth_weekday_on_or_after(year: int, month: int, day: int, weekday: int) -> date:
    d = date(year, month, day)
    return d + timedelta(days=(weekday - d.weekday()) % 7)


def upcoming(today: date | None = None, days: int = 35) -> list[Event]:
    today = today or datetime.now(ET).date()
    end = today + timedelta(days=days)
    ev: list[Event] = []

    for w in eia_wpsr_dates(today, end):
        ev.append(Event(w, "EIA Weekly Petroleum Status Report", "EIA",
                        "https://www.eia.gov/petroleum/supply/weekly/schedule.php"))
    for w in _weekly(today, end, 4, time(13, 0)):
        ev.append(Event(w, "Baker Hughes US rig count", "Baker Hughes", "https://rigcount.bakerhughes.com/"))
    for w in _weekly(today, end, 4, time(15, 30)):
        ev.append(Event(w, "CFTC Commitments of Traders", "CFTC",
                        "https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm"))

    m = date(today.year, today.month, 1)
    while m <= end:
        y, mo = m.year, m.month
        ev += [
            Event(datetime.combine(_nth_weekday_on_or_after(y, mo, 6, 1), time(12, 0), ET),
                  "EIA Short-Term Energy Outlook", "EIA", "https://www.eia.gov/outlooks/steo/release_schedule.php",
                  estimated=True, note="1st Tue after the 5th"),
            Event(datetime.combine(_nth_weekday_on_or_after(y, mo, 11, 0) + timedelta(days=1), time(7, 0), ET),
                  "OPEC Monthly Oil Market Report", "OPEC", "https://www.opec.org/opec_web/en/publications/338.htm",
                  estimated=True, note="Mid-month"),
            Event(datetime.combine(_nth_weekday_on_or_after(y, mo, 11, 0) + timedelta(days=3), time(4, 0), ET),
                  "IEA Oil Market Report", "IEA", "https://www.iea.org/about/oil-market-report-schedule",
                  estimated=True, note="Mid-month"),
        ]
        m = date(y + (mo == 12), mo % 12 + 1, 1)

    now = datetime.now(ET)
    return sorted((e for e in ev if e.when >= now and e.when.date() <= end), key=lambda e: e.when)


def next_wpsr(after: datetime | None = None) -> datetime:
    after = after or datetime.now(ET)
    return next(d for d in eia_wpsr_dates(after.date(), after.date() + timedelta(days=21)) if d > after)
