#!/usr/bin/env python3
"""TG 换绑数据迁移测试"""


def test_transfer_tg_binding_assets_moves_related_records(test_db):
    old_tg_id = 10001
    new_tg_id = 20002
    plex_id = 9001
    emby_id = "emby-9001"
    cursor = test_db.cur

    test_db.add_plex_user(
        plex_id=plex_id,
        tg_id=old_tg_id,
        plex_email="old@example.com",
        plex_username="oldplex",
        credits=0,
    )
    test_db.add_emby_user(
        "oldemby",
        emby_id=emby_id,
        tg_id=old_tg_id,
    )
    test_db.add_user_data(tg_id=old_tg_id, credits=150.0, donation=20.0)
    test_db.add_user_data(tg_id=new_tg_id, credits=10.0, donation=5.0)

    test_db.add_invitation_code("invite-old", owner=old_tg_id)

    cursor.execute(
        """
        INSERT INTO checkin_stats (tg_id, checkin_date, streak, month, credits_earned)
        VALUES (?, '2026-03-01', 1, '2026-03', 2.0)
        """,
        (old_tg_id,),
    )
    cursor.execute(
        """
        INSERT INTO checkin_stats (tg_id, checkin_date, streak, month, credits_earned)
        VALUES (?, '2026-03-02', 2, '2026-03', 2.0)
        """,
        (old_tg_id,),
    )
    cursor.execute(
        """
        INSERT INTO checkin_stats (tg_id, checkin_date, streak, month, credits_earned)
        VALUES (?, '2026-03-02', 3, '2026-03', 1.5)
        """,
        (new_tg_id,),
    )

    cursor.execute(
        """
        INSERT INTO user_medals (tg_id, medal_code, source, acquired_at, is_active)
        VALUES (?, 'special_contribution', 'shop', 100, 1)
        """,
        (old_tg_id,),
    )
    cursor.execute(
        """
        INSERT INTO user_medals (tg_id, medal_code, source, acquired_at, is_active)
        VALUES (?, 'checkin_top_2_ox', 'checkin_total_rank', 120, 1)
        """,
        (old_tg_id,),
    )
    cursor.execute(
        """
        INSERT INTO user_medals (tg_id, medal_code, source, acquired_at, is_active)
        VALUES (?, 'special_contribution', 'shop', 300, 1)
        """,
        (new_tg_id,),
    )

    cursor.execute(
        """
        INSERT INTO wheel_stats (tg_id, item_name, credits_change, timestamp, date)
        VALUES (?, '积分 +10', 10, 1, '2026-03-01')
        """,
        (old_tg_id,),
    )
    cursor.execute(
        """
        INSERT INTO blackjack_stats
            (tg_id, bet_amount, result, credits_change, player_score, dealer_score, timestamp, date)
        VALUES (?, 5, 'win', 5, 20, 18, 2, '2026-03-02')
        """,
        (old_tg_id,),
    )
    cursor.execute(
        """
        INSERT INTO auctions
            (title, description, starting_price, current_price, end_time, created_by, created_at, is_active, winner_id, bid_count)
        VALUES ('auction', 'desc', 1, 5, 999999, ?, 1, 0, ?, 1)
        """,
        (old_tg_id, old_tg_id),
    )
    auction_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO auction_bids (auction_id, bidder_id, bid_amount, bid_time)
        VALUES (?, ?, 5, 10)
        """,
        (auction_id, old_tg_id),
    )
    cursor.execute(
        "INSERT INTO overseerr VALUES (?, ?, ?)",
        (7001, "old-overseerr@example.com", old_tg_id),
    )
    cursor.execute(
        """
        INSERT INTO group_member_left_status
            (tg_id, left_time, group_id, is_processed, warning_sent, last_warning_time)
        VALUES (?, 100, 1, 0, 0, 0)
        """,
        (old_tg_id,),
    )
    cursor.execute(
        """
        INSERT INTO group_member_left_status
            (tg_id, left_time, group_id, is_processed, warning_sent, last_warning_time)
        VALUES (?, 200, 1, 0, 0, 0)
        """,
        (new_tg_id,),
    )
    test_db.con.commit()

    result = test_db.transfer_tg_binding_assets(
        old_tg_id,
        new_tg_id,
        fee=100.0,
        plex_id=plex_id,
        emby_id=emby_id,
    )

    assert result["remaining_credits"] == 50.0
    assert result["final_credits"] == 60.0
    assert result["final_donation"] == 25.0
    assert result["final_debt_since"] is None

    stats = test_db.get_stats_by_tg_id(new_tg_id)
    assert stats is not None
    assert stats["credits"] == 60.0
    assert stats["donation"] == 25.0
    assert test_db.get_stats_by_tg_id(old_tg_id) is None

    assert test_db.get_plex_info_by_tg_id(new_tg_id)["plex_id"] == plex_id
    assert test_db.get_emby_info_by_tg_id(new_tg_id)["emby_id"] == emby_id
    assert test_db.get_plex_info_by_tg_id(old_tg_id) is None
    assert test_db.get_emby_info_by_tg_id(old_tg_id) is None

    invite = test_db.cur.execute(
        "SELECT owner FROM invitation WHERE code = 'invite-old'"
    ).fetchone()
    assert invite["owner"] == new_tg_id

    checkins = test_db.cur.execute(
        """
        SELECT checkin_date, streak, credits_earned
        FROM checkin_stats
        WHERE tg_id = ?
        ORDER BY checkin_date ASC
        """,
        (new_tg_id,),
    ).fetchall()
    assert len(checkins) == 2
    assert checkins[0]["checkin_date"] == "2026-03-01"
    assert checkins[1]["checkin_date"] == "2026-03-02"
    assert checkins[1]["streak"] == 3
    assert checkins[1]["credits_earned"] == 3.5

    medals = test_db.cur.execute(
        """
        SELECT medal_code, acquired_at
        FROM user_medals
        WHERE tg_id = ?
        ORDER BY medal_code ASC
        """,
        (new_tg_id,),
    ).fetchall()
    assert {row["medal_code"] for row in medals} == {
        "checkin_top_2_ox",
        "special_contribution",
    }
    special_medal = next(row for row in medals if row["medal_code"] == "special_contribution")
    assert special_medal["acquired_at"] == 100

    assert test_db.cur.execute(
        "SELECT COUNT(*) FROM user_medals WHERE tg_id = ?", (old_tg_id,)
    ).fetchone()[0] == 0
    assert test_db.cur.execute(
        "SELECT COUNT(*) FROM wheel_stats WHERE tg_id = ?", (new_tg_id,)
    ).fetchone()[0] == 1
    assert test_db.cur.execute(
        "SELECT COUNT(*) FROM blackjack_stats WHERE tg_id = ?", (new_tg_id,)
    ).fetchone()[0] == 1
    assert test_db.cur.execute(
        "SELECT COUNT(*) FROM auctions WHERE created_by = ? AND winner_id = ?",
        (new_tg_id, new_tg_id),
    ).fetchone()[0] == 1
    assert test_db.cur.execute(
        "SELECT COUNT(*) FROM auction_bids WHERE bidder_id = ?", (new_tg_id,)
    ).fetchone()[0] == 1
    assert test_db.cur.execute(
        "SELECT COUNT(*) FROM overseerr WHERE tg_id = ?", (new_tg_id,)
    ).fetchone()[0] == 1
    assert test_db.cur.execute(
        "SELECT COUNT(*) FROM group_member_left_status WHERE tg_id IN (?, ?)",
        (old_tg_id, new_tg_id),
    ).fetchone()[0] == 0


def test_transfer_tg_binding_assets_allows_missing_old_stats(test_db):
    old_tg_id = 30003
    new_tg_id = 40004
    plex_id = 9100

    test_db.add_plex_user(
        plex_id=plex_id,
        tg_id=old_tg_id,
        plex_email="legacy@example.com",
        plex_username="legacyplex",
        credits=0,
    )

    result = test_db.transfer_tg_binding_assets(
        old_tg_id,
        new_tg_id,
        fee=100.0,
        plex_id=plex_id,
    )

    stats = test_db.get_stats_by_tg_id(new_tg_id)
    assert stats is not None
    assert result["remaining_credits"] == -100.0
    assert result["final_credits"] == -100.0
    assert stats["credits"] == -100.0
    assert stats["debt_since"] is not None
    assert test_db.get_plex_info_by_tg_id(new_tg_id)["plex_id"] == plex_id
