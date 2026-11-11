"""NYSE close deadlines in UTC; Stockholm/US DST and exchange holidays are independent."""
from datetime import timedelta
import exchange_calendars
import pandas as pd


def close_status(now):
    calendar = exchange_calendars.get_calendar('XNYS')
    timestamp = pd.Timestamp(now)
    sessions = calendar.sessions_in_range(timestamp.date()-timedelta(days=14), timestamp.date()+timedelta(days=14))
    completed = [s for s in sessions if calendar.session_close(s)+pd.Timedelta(minutes=15) <= timestamp]
    latest = completed[-1]
    following = sessions[sessions.get_loc(latest)+1]
    return dict(calendar='XNYS', expected_price_as_of=latest.date().isoformat(),
                close_at=calendar.session_close(latest).isoformat(),
                next_session=following.date().isoformat(),
                next_close_due=(calendar.session_close(following)+pd.Timedelta(minutes=15)).isoformat())
