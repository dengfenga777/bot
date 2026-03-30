#!/usr/bin/env python3
"""勋章系统测试"""

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


def test_sync_checkin_total_rank_medals_assigns_top3(test_db):
    start = date(2026, 1, 1)
    users = [
        (10001, 12),
        (10002, 11),
        (10003, 10),
        (10004, 9),
    ]

    for tg_id, credits in users:
        test_db.add_user_data(tg_id=tg_id, credits=credits, donation=0)

    _add_checkins(test_db, 10001, 12, start)
    _add_checkins(test_db, 10002, 11, start)
    _add_checkins(test_db, 10003, 10, start)
    _add_checkins(test_db, 10004, 9, start)

    test_db.sync_checkin_total_rank_medals()

    user1_medals = test_db.get_user_medals(10001)
    user2_medals = test_db.get_user_medals(10002)
    user3_medals = test_db.get_user_medals(10003)
    user4_medals = test_db.get_user_medals(10004)

    assert [medal["code"] for medal in user1_medals] == ["checkin_top_1_ox"]
    assert [medal["code"] for medal in user2_medals] == ["checkin_top_2_ox"]
    assert [medal["code"] for medal in user3_medals] == ["checkin_top_3_ox"]
    assert user4_medals == []

    assert test_db.get_user_medal_multiplier(10001) == 1.5
    assert test_db.get_user_medal_multiplier(10002) == 1.3
    assert test_db.get_user_medal_multiplier(10003) == 1.1
    assert test_db.get_user_medal_multiplier(10004) == 1.0


def test_checkin_rank_medals_are_hidden_from_shop(test_db):
    test_db.add_user_data(tg_id=20001, credits=100, donation=0)
    payload = test_db.get_medal_shop_payload(20001)
    shop_codes = {item["code"] for item in payload["shop_items"]}

    assert "special_contribution" in shop_codes
    assert "checkin_top_1_ox" not in shop_codes
    assert "checkin_top_2_ox" not in shop_codes
    assert "checkin_top_3_ox" not in shop_codes


def test_sync_checkin_total_rank_medals_updates_when_rank_changes(test_db):
    start = date(2026, 2, 1)
    for tg_id in (30001, 30002, 30003, 30004):
        test_db.add_user_data(tg_id=tg_id, credits=100, donation=0)

    _add_checkins(test_db, 30001, 8, start)
    _add_checkins(test_db, 30002, 7, start)
    _add_checkins(test_db, 30003, 6, start)
    test_db.sync_checkin_total_rank_medals()

    assert [medal["code"] for medal in test_db.get_user_medals(30003)] == ["checkin_top_3_ox"]

    _add_checkins(test_db, 30004, 9, start)
    test_db.sync_checkin_total_rank_medals()

    assert [medal["code"] for medal in test_db.get_user_medals(30004)] == ["checkin_top_1_ox"]
    assert [medal["code"] for medal in test_db.get_user_medals(30001)] == ["checkin_top_2_ox"]
    assert [medal["code"] for medal in test_db.get_user_medals(30002)] == ["checkin_top_3_ox"]
    assert test_db.get_user_medals(30003) == []
