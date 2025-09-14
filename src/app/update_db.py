import asyncio
import json
import re
from datetime import datetime, timedelta
from time import time
from urllib.parse import parse_qs, urlparse
from uuid import NAMESPACE_URL, uuid3

from app.cache import (
    emby_api_key_cache,
    plex_token_cache,
    user_credits_cache,
)
from app.config import settings
from app.db import DB
from app.emby import Emby
from app.log import logger
from app.plex import Plex
from app.tautulli import Tautulli
from app.utils import (
    get_user_name_from_tg_id,
    get_user_total_duration,
    send_message_by_url,
)
import requests
from typing import Optional


def update_plex_credits():
    """更新花币及观看时长"""
    logger.info("开始更新 Plex 用户花币及观看时长")
    _db = DB()
    notification_tasks = []
    try:
        # 获取一天内的观看时长
        duration = get_user_total_duration(
            Tautulli().get_home_stats(
                1, "duration", len(Plex().users_by_id), "top_users"
            )
        )
        # update credits and watched_time
        res = _db.cur.execute("select plex_id from user")
        users = res.fetchall()
        for user in users:
            plex_id = user[0]
            play_duration = round(min(float(duration.get(plex_id, 0)), 24), 2)
            if play_duration == 0:
                continue
            # 最大记 8h
            credits_inc = min(play_duration, 8)
            res = _db.cur.execute(
                "SELECT credits,watched_time,tg_id,plex_username,is_premium FROM user WHERE plex_id=?",
                (plex_id,),
            ).fetchone()
            if not res:
                continue
            watched_time_init = res[1]
            tg_id = res[2]
            plex_username = res[3]
            is_premium = res[4]
            # 已移除基于流量的扣费逻辑
            traffic_cost_credits = 0
            if not tg_id:
                credits_init = res[0]
                credits = credits_init + credits_inc
                watched_time = watched_time_init + play_duration
                _db.cur.execute(
                    "UPDATE user SET credits=?,watched_time=? WHERE plex_id=?",
                    (credits, watched_time, plex_id),
                )
            else:
                credits_init = _db.cur.execute(
                    "SELECT credits FROM statistics WHERE tg_id=?", (tg_id,)
                ).fetchone()[0]
                credits = credits_init + credits_inc
                watched_time = watched_time_init + play_duration
                _db.cur.execute(
                    "UPDATE user SET watched_time=? WHERE plex_id=?",
                    (watched_time, plex_id),
                )
                _db.cur.execute(
                    "UPDATE statistics SET credits=? WHERE tg_id=?", (credits, tg_id)
                )
                if play_duration > 0:
                    # 需要发送通知
                    notification_tasks.append(
                        (
                            tg_id,
                            f"""
Plex 观看花币更新通知
====================

新增观看时长: {round(play_duration, 2)} 小时
新增观看花币：{round(credits_inc, 2)}
花币变化：{round(credits_inc, 2)}

--------------------

当前总花币：{round(credits, 2)}
当前总观看时长：{round(watched_time, 2)} 小时

====================""",
                        )
                    )

            logger.info(
                f"更新 Plex 用户 {plex_username} ({plex_id}) 的花币和观看时长: "
                f"新增观看时长 {round(play_duration, 2)} 小时，新增观看花币 {round(credits_inc, 2)}"
            )

    except Exception as e:
        logger.error(f"更新 Plex 用户花币及观看时长失败: {e}")
        notification_tasks.append(
            (
                settings.ADMIN_CHAT_ID[0],
                f"更新 Plex 用户花币及观看时长失败: {e}",
            )
        )
        return notification_tasks
    else:
        _db.con.commit()
        logger.info("Plex 用户花币及观看时长更新完成")
        return notification_tasks
    finally:
        _db.close()


def update_emby_credits():
    """更新 emby 花币及观看时长"""
    logger.info("开始更新 Emby 用户花币及观看时长")
    # 获取所有用户的观看时长
    emby = Emby()
    _db = DB()
    notification_tasks = []
    try:
        duration = emby.get_user_total_play_time()
        # 获取数据库中的观看时长信息
        users = _db.cur.execute(
            "select emby_id, tg_id, emby_watched_time, emby_credits, emby_username, is_premium from emby_user"
        ).fetchall()
        for user in users:
            playduration = round(float(duration.get(user[0], 0)) / 3600, 2)
            if playduration == 0:
                continue
            # 最大记 8
            credits_inc = min(playduration - user[2], 8)
            emby_username, is_premium = user[4], user[5]
            # 已移除基于流量的扣费逻辑
            traffic_cost_credits = 0

            if not user[1]:
                _credits = user[3] + credits_inc
                _db.cur.execute(
                    "UPDATE emby_user SET emby_watched_time=?,emby_credits=? WHERE emby_id=?",
                    (playduration, _credits, user[0]),
                )
            else:
                stats_info = _db.get_stats_by_tg_id(user[1])
                # statistics 表中有数据
                if stats_info:
                    credits_init = stats_info[2]
                    _credits = credits_init + credits_inc
                    _db.update_user_credits(_credits, tg_id=user[1])
                else:
                    # 清空 emby_user 表中积分信息
                    _db.update_user_credits(0, emby_id=user[0])
                    # 在 statistic 表中增加用户数据
                    _credits = user[3] + credits_inc
                    _db.add_user_data(user[1], credits=_credits)
                # 更新 emby_user 表中观看时间
                _db.cur.execute(
                    "UPDATE emby_user SET emby_watched_time=? WHERE emby_id=?",
                    (playduration, user[0]),
                )
                if (playduration - user[2]) > 0:
                    # 需要发送消息通知
                    notification_tasks.append(
                        (
                            user[1],
                            f"""
Emby 观看花币更新通知
====================

新增观看时长: {round(playduration - user[2], 2)} 小时
新增观看花币：{round(credits_inc, 2)}
花币变化：{round(credits_inc, 2)}

--------------------

当前总花币：{round(_credits, 2)}
当前总观看时长：{round(playduration, 2)} 小时

====================""",
                        )
                    )

            logger.info(
                f"更新 Emby 用户 {emby_username} ({user[0]}) 的花币和观看时长: "
                f"新增观看时长 {round(playduration - user[2], 2)} 小时，新增观看花币 {round(credits_inc, 2)}"
            )
    except Exception as e:
        logger.error(f"更新 Emby 用户花币及观看时长失败: {e}")
        notification_tasks.append(
            (
                settings.ADMIN_CHAT_ID[0],
                f"更新 Emby 用户花币及观看时长失败: {e}",
            )
        )
        return notification_tasks
    else:
        _db.con.commit()
        logger.info("Emby 用户花币及观看时长更新完成")
        return notification_tasks
    finally:
        _db.close()


async def update_credits():
    """更新 Plex 和 Emby 用户花币及观看时长"""
    notification_tasks = update_plex_credits()
    notification_tasks.extend(update_emby_credits())
    for tg_id, text in notification_tasks:
        # 发送通知消息，静默模式
        await send_message_by_url(chat_id=tg_id, text=text, disable_notification=True)
        await asyncio.sleep(1)


def _is_emby_session_playing(sess: dict) -> bool:
    now = sess.get("NowPlayingItem") or {}
    media_type = str(now.get("MediaType", "")).lower()
    if media_type not in {"video", "audio"}:
        return False
    ps = sess.get("PlayState") or {}
    if ps.get("IsPaused") is True:
        return False
    return True


def collect_emby_live_watch() -> None:
    """每分钟采集一次 Emby 在线“在播”会话并本地累计时长（无需插件）"""
    try:
        if not (settings.EMBY_BASE_URL and settings.EMBY_API_TOKEN):
            return
        emby = Emby()
        resp = requests.get(
            f"{emby.base_url.rstrip('/')}/Sessions",
            params={"api_key": emby.api_token, "ActiveWithinSeconds": 600},
            timeout=8,
        )
        if not resp.ok:
            logger.error(f"collect_emby_live_watch sessions failed: {resp.status_code}")
            return
        sessions = resp.json() or []
        playing = [s for s in sessions if _is_emby_session_playing(s)]
        if not playing:
            return
        from datetime import datetime
        date_str = datetime.now(settings.TZ).strftime("%Y-%m-%d")
        db = DB()
        for s in playing:
            emby_id = s.get("UserId") or ""
            username = s.get("UserName") or ""
            if not emby_id:
                continue
            db.add_emby_watch_seconds(date_str, str(emby_id), username, seconds=60)
        db.close()
    except Exception as e:
        logger.error(f"collect_emby_live_watch failed: {e}")


async def push_emby_watch_rank(days: int = 1, top_n: int = 10, target_chat_id: Optional[int] = None) -> None:
    """推送 Emby 观看时长排行榜到群（每天/每周总结）

    优先走 user_usage_stats 插件（与你另一个项目一致）；若不可用/无数据，则使用本地聚合。
    """
    try:
        db = DB()
        emby = Emby()

        # 1) 插件方式（强制与调试一致：DateCreated + delta + ReplaceUserId=True）
        results = []
        try:
            end = datetime.now(settings.TZ)
            start = end - timedelta(days=days if days > 0 else 1)
            start_time = start.strftime("%Y-%m-%d %H:%M:%S")
            end_time = end.strftime("%Y-%m-%d %H:%M:%S")
            sql = (
                "SELECT UserId, SUM(PlayDuration - PauseDuration) AS WatchTime "
                "FROM PlaybackActivity "
                f"WHERE DateCreated >= '{start_time}' AND DateCreated < '{end_time}' "
                "GROUP BY UserId ORDER BY WatchTime DESC"
            )
            headers = {"accept": "application/json", "Content-Type": "application/json"}
            paths = [
                "/user_usage_stats/submit_custom_query",
                "/emby/user_usage_stats/submit_custom_query",
            ]
            rows = []
            for path in paths:
                try:
                    resp = requests.post(
                        url=emby.base_url.rstrip("/") + path,
                        params={"api_key": emby.api_token},
                        headers=headers,
                        json={"CustomQueryString": sql, "ReplaceUserId": True},
                        timeout=8,
                    )
                    if resp.ok:
                        js = resp.json() or {}
                        rows = js.get("results", []) or []
                        if rows:
                            break
                except Exception:
                    continue
            for r in rows[:top_n or 999]:
                try:
                    uid_or_name, secs = r
                    hours = float(secs or 0) / 3600.0
                    results.append((str(uid_or_name), hours))
                except Exception:
                    continue
        except Exception:
            results = []
        lines: list[str] = []
        if results:
            for idx, (emby_user_id, hours) in enumerate(results[:top_n], start=1):
                info = db.get_emby_info_by_emby_id(emby_user_id)
                if info:
                    emby_username = info[0]
                    tg_id = info[2]
                    name = (
                        get_user_name_from_tg_id(tg_id)
                        if tg_id is not None
                        else emby_username or emby_user_id
                    )
                else:
                    name = emby_user_id
                lines.append(f"{idx}. {name}: {hours:.2f} 小时")
        else:
            # 2) 本地聚合（无需插件）
            aggregated = db.get_emby_watch_rank_last_days(days=days, limit=top_n)
            if not aggregated:
                if settings.ADMIN_CHAT_ID:
                    await send_message_by_url(
                        chat_id=settings.ADMIN_CHAT_ID[0],
                        text=f"Emby 观看时长榜通知：近{days}天无数据",
                        disable_notification=True,
                    )
                return

            def resolve_name(emby_id: str, username_hint: str):
                info = db.get_emby_info_by_emby_id(emby_id)
                if info:
                    emby_username = info[0]
                    tg_id = info[2]
                    return (
                        get_user_name_from_tg_id(tg_id)
                        if tg_id is not None
                        else emby_username or username_hint or emby_id
                    )
                return username_hint or emby_id

            for idx, (emby_user_id, username, hours) in enumerate(aggregated, start=1):
                name = resolve_name(emby_user_id, username)
                lines.append(f"{idx}. {name}: {hours:.2f} 小时")

        title = (
            f"【Emby 观看时长榜 - 日榜】\n\n" if days == 1 else f"【Emby 观看时长榜 - 近{days}天】\n\n"
        )
        text = title + "\n".join(lines)
        # 发送目标：优先当前会话；否则发给所有管理员
        targets = []
        if target_chat_id is not None:
            targets = [target_chat_id]
        elif settings.ADMIN_CHAT_ID:
            # 支持多个目标
            targets = list(settings.ADMIN_CHAT_ID)
        for tgt in targets:
            await send_message_by_url(chat_id=tgt, text=text, disable_notification=True)
    except Exception as e:
        logger.error(f"push_emby_watch_rank failed: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass


def update_plex_info():
    """更新 plex 用户信息"""
    _db = DB()
    _plex = Plex()
    try:
        users = _plex.users_by_id
        for uid, user in users.items():
            email = user[1].email
            username = user[0]
            _db.cur.execute(
                "UPDATE user SET plex_username=?,plex_email=? WHERE plex_id=?",
                (username, email, uid),
            )
        # 更新所有用户的头像
        _plex.update_all_user_avatars()
    except Exception as e:
        print(e)
    else:
        _db.con.commit()
    finally:
        _db.close()


def update_all_lib():
    """更新用户资料库权限状态"""
    _db = DB()
    _plex = Plex()
    try:
        users = _plex.users_by_email
        all_libs = _plex.get_libraries()
        for email, user in users.items():
            if not email:
                continue
            _info = _db.cur.execute("select * from user where plex_email=?", (email,))
            _info = _info.fetchone()
            if not _info:
                continue
            cur_libs = _plex.get_user_shared_libs_by_id(user[0])
            all_lib_flag = 1 if not set(all_libs).difference(set(cur_libs)) else 0
            _db.cur.execute(
                "UPDATE user SET all_lib=? WHERE plex_email=?", (all_lib_flag, email)
            )
    except Exception as e:
        print(e)
    else:
        _db.con.commit()
    finally:
        _db.close()


def update_watched_time():
    """更新用户观看时长"""
    duration = get_user_total_duration(
        Tautulli().get_home_stats(
            36500, "duration", len(Plex().users_by_id), "top_users"
        )
    )
    _db = DB()
    try:
        res = _db.cur.execute("select plex_id from user")
        users = res.fetchall()
        for user in users:
            plex_id = user[0]
            watched_time = duration.get(plex_id, 0)
            _db.cur.execute(
                "UPDATE user SET watched_time=? WHERE plex_id=?",
                (watched_time, plex_id),
            )

    except Exception as e:
        print(e)
    else:
        _db.con.commit()
    finally:
        _db.close()


def add_all_plex_user():
    """将所有 plex 用户均加入到数据库中"""

    duration = get_user_total_duration(
        Tautulli().get_home_stats(
            36500, "duration", len(Plex().users_by_id), "top_users"
        )
    )
    _plex = Plex()
    users = [user for user in _plex.my_plex_account.users()]
    users.append(_plex.my_plex_account)
    _db = DB()
    all_libs = Plex().get_libraries()
    try:
        _existing_users = _db.cur.execute("select plex_id from user").fetchall()
        existing_users = [user[0] for user in _existing_users]
        for user in users:
            # 已存在用户及未接受邀请用户跳过
            if user.id in existing_users or (not user.email):
                continue
            watched_time = duration.get(user.id, 0)
            try:
                cur_libs = _plex.get_user_shared_libs_by_id(user.id)
            # 跳过分享给我的用户
            except Exception as e:
                print(e)
                continue
            all_lib_flag = 1 if not set(all_libs).difference(set(cur_libs)) else 0
            _db.add_plex_user(
                plex_id=user.id,
                tg_id=None,
                plex_email=user.email,
                plex_username=user.username,
                credits=watched_time,
                all_lib=all_lib_flag,
                watched_time=watched_time,
            )

    except Exception as e:
        print(e)
    else:
        _db.con.commit()
    finally:
        _db.close()


def update_donation_credits(old_multiplier, new_multiplier):
    """
    更新捐赠花币

    Args:
        old_multiplier: 旧的花币倍数
        new_multiplier: 新的花币倍数
    """
    try:
        db = DB()
        # 获取所有捐赠记录
        donations = db.cur.execute(
            "SELECT tg_id, donation, credits FROM statistics WHERE donation > 0"
        ).fetchall()

        for tg_id, donation, credits in donations:
            # 计算新的花币
            new_credits = round(
                credits + donation * (new_multiplier - old_multiplier), 2
            )
            # 更新数据库
            db.cur.execute(
                "UPDATE statistics SET credits = ? WHERE tg_id = ?",
                (new_credits, tg_id),
            )
            logger.info(
                f"用户 {tg_id} 捐赠：{donation}, 更新花币: {credits} -> {new_credits}"
            )

        db.con.commit()
    except Exception as e:
        logger.error(str(e))
    finally:
        db.close()


def add_redeem_code(tg_id=None, num=1, is_privileged=False):
    """
    生成邀请码

    Args:
        tg_id: 用户ID，None表示为所有用户生成
        num: 生成数量
        is_privileged: 是否生成特权邀请码
    """
    from app.config import settings

    db = DB()
    if tg_id is None:
        tg_id = [
            u[0] for u in db.cur.execute("SELECT tg_id FROM statistics").fetchall()
        ]
    elif not isinstance(tg_id, list):
        tg_id = [tg_id]
    try:
        for uid in tg_id:
            for _ in range(num):
                code = uuid3(NAMESPACE_URL, str(uid + time())).hex
                db.add_invitation_code(code, owner=uid)

                # 如果是特权邀请码，添加到特权码列表
                if is_privileged:
                    if code not in settings.PRIVILEGED_CODES:
                        settings.PRIVILEGED_CODES.append(code)
                        # 保存到配置文件
                        settings.save_config_to_env_file(
                            {"PRIVILEGED_CODES": ",".join(settings.PRIVILEGED_CODES)}
                        )
                        logger.info(
                            f"添加特权邀请码 {code} 给用户 {get_user_name_from_tg_id(uid)}"
                        )
                else:
                    logger.info(
                        f"添加邀请码 {code} 给用户 {get_user_name_from_tg_id(uid)}"
                    )
    except Exception as e:
        print(e)
    else:
        db.con.commit()
    finally:
        db.close()


async def finish_expired_auctions_job():
    """定时任务：结束过期的竞拍活动"""
    try:
        db = DB()
        finished_auctions = db.finish_expired_auctions()
        # 通知用户
        for autction in finished_auctions:
            await send_message_by_url(
                autction.get("winner_id"),
                f"恭喜你，竞拍 {autction['title']} 获胜！最终出价为 {autction['final_price']} 花币",
            )
            if not autction.get("credits_reduced", False):
                # 如果未扣除花币，通知管理员
                for chat_id in settings.ADMIN_CHAT_ID:
                    await send_message_by_url(
                        chat_id=chat_id,
                        text=f"用户 {autction.get('winner_id')} 在竞拍 {autction['title']} 中获胜，但未扣除花币。",
                    )
        return finished_auctions
    except Exception as e:
        logger.error(f"自动结束过期竞拍失败: {e}")
    finally:
        db.close()


async def update_line_traffic_stats(count: int = 0):
    """线路流量统计功能已移除"""
    return None


def rewrite_users_credits_to_redis():
    """
    将用户积分信息写入 redis 缓存
    """
    _db = DB()
    try:
        # 从 statistics 表中获取所有用户的积分信息
        stats = _db.cur.execute("SELECT tg_id, credits FROM statistics").fetchall()
        user_stats = {tg_id: credits for tg_id, credits in stats}
        # 获取 Plex 用户信息
        plex_users = _db.cur.execute(
            "SELECT plex_id, tg_id, credits, plex_username FROM user"
        ).fetchall()
        for user in plex_users:
            tg_id = user[1]
            credits = user[2]
            plex_username = user[3]
            if tg_id:
                credits = user_stats.get(tg_id, 0)
            user_credits_cache.put(f"plex:{plex_username.lower()}", credits)
        # 获取 Emby 用户信息
        emby_users = _db.cur.execute(
            "SELECT emby_id, tg_id, emby_credits, emby_username FROM emby_user"
        ).fetchall()
        for user in emby_users:
            tg_id = user[1]
            credits = user[2]
            emby_username = user[3]
            if tg_id:
                credits = user_stats.get(tg_id, 0)
            user_credits_cache.put(f"emby:{emby_username.lower()}", credits)
    except Exception as e:
        logger.error(f"检查用户积分时发生错误: {e}")
    finally:
        _db.close()


if __name__ == "__main__":
    update_plex_credits()
    update_plex_info()
    # add_all_plex_user()
    update_emby_credits()
    # 测试流量统计更新
    # update_line_traffic_stats()
