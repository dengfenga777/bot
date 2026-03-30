#!/usr/bin/env python3
"""签到排行排序测试"""

from datetime import date, timedelta


def _add_checkins(db, tg_id: int, days: int, start: date):
    for offset in range(days):
        current = start + timedelta(days=offset)
        db.add_checkin(
            tg_id=tg_id,
            checkin_date=current.isoformat(),
            streak=offset + 1,
            month=current.strftime("%Y-%m"),
            credits_earned=1.0,
        )


def test_monthly_leaderboard_prefers_earlier_checkin_when_days_tie(test_db):
    start = date(2026, 3, 1)
    _add_checkins(test_db, 1001, 5, start)
    _add_checkins(test_db, 1002, 5, start)

    rows = test_db.get_checkin_monthly_leaderboard("2026-03")

    assert [row["tg_id"] for row in rows[:2]] == [1001, 1002]


def test_total_leaderboard_prefers_earlier_checkin_when_days_tie(test_db):
    start = date(2026, 1, 1)
    _add_checkins(test_db, 2001, 7, start)
    _add_checkins(test_db, 2002, 7, start)

    rows = test_db.get_checkin_total_leaderboard(limit=2)

    assert [row["tg_id"] for row in rows] == [2001, 2002]


def test_total_rank_uses_earlier_checkin_as_tiebreaker(test_db):
    start = date(2026, 2, 1)
    _add_checkins(test_db, 3001, 6, start)
    _add_checkins(test_db, 3002, 6, start)
    _add_checkins(test_db, 3003, 5, start)

    assert test_db.get_checkin_total_rank(3001) == 1
    assert test_db.get_checkin_total_rank(3002) == 2
    assert test_db.get_checkin_total_rank(3003) == 3
