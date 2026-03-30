import asyncio
import json
from datetime import datetime
from time import time
from urllib.parse import parse_qs, urlparse
from uuid import NAMESPACE_URL, uuid3

import httpx

from app.cache import (
    emby_api_key_cache,
    plex_token_cache,
    stream_traffic_cache,
    user_credits_cache,
    user_info_cache,
)
from app.config import settings
from app.db import DB
from app.invitation_utils import INVITATION_EXPIRE_DAYS, generate_unique_invitation_code
from app.emby import Emby
from app.log import logger
from app.plex import Plex
from app.tautulli import Tautulli
from app.utils.utils import (
    get_user_name_from_tg_id,
    get_user_total_duration,
    send_message_by_url,
)


def _build_credit_bonus_lines(dual_bind_multiplier: float, medal_multiplier: float):
    bonus_lines = []
    if dual_bind_multiplier > 1.0:
        bonus_lines.append(f"   🎁  双账号加成：×{dual_bind_multiplier:.2f}")
    if medal_multiplier > 1.0:
        bonus_lines.append(f"   🏅  勋章加成：×{medal_multiplier:.2f}")
    return "\n".join(bonus_lines) + ("\n" if bonus_lines else "")


def update_plex_credits():
    """更新积分及观看时长"""
    logger.info("开始更新 Plex 用户积分及观看时长")
    _db = DB()
    notification_tasks = []
    try:
        _db.sync_checkin_total_rank_medals()
        duration = get_user_total_duration(
            Tautulli().get_home_stats(
                1, "duration", len(Plex().users_by_id), "top_users"
            )
        )
        res = _db.cur.execute("select plex_id from user")
        users = res.fetchall()
        for user in users:
            plex_id = user[0]
            play_duration = round(min(float(duration.get(plex_id, 0)), 24), 2)
            if play_duration == 0:
                continue
            res = _db.cur.execute(
                "SELECT credits,watched_time,tg_id,plex_username FROM user WHERE plex_id=?",
                (plex_id,),
            ).fetchone()
            if not res:
                continue
            watched_time_init = res[1]
            tg_id = res[2]
            plex_username = res[3]

            # 双账号绑定加成
            if tg_id:
                has_emby = bool(_db.get_emby_info_by_tg_id(tg_id))
                dual_bind_multiplier = settings.DUAL_BIND_MULTIPLIER if has_emby else 1.0
                medal_multiplier = _db.get_user_medal_multiplier(tg_id)
            else:
                dual_bind_multiplier = 1.0
                medal_multiplier = 1.0
            multiplier = dual_bind_multiplier * medal_multiplier
            base_credits = min(play_duration, 8)
            credits_inc = round(base_credits * multiplier, 2)

            # 异常观看检测
            ABUSE_THRESHOLD = settings.ABUSE_WATCH_THRESHOLD
            is_abusive = play_duration > ABUSE_THRESHOLD
            if is_abusive:
                credits_inc = 0

            watched_time = watched_time_init + play_duration
            if not tg_id:
                credits_init = res[0]
                credits = credits_init if is_abusive else credits_init + credits_inc
                _db.cur.execute(
                    "UPDATE user SET credits=?,watched_time=? WHERE plex_id=?",
                    (credits, watched_time, plex_id),
                )
            else:
                credits_init = _db.cur.execute(
                    "SELECT credits FROM statistics WHERE tg_id=?", (tg_id,)
                ).fetchone()[0]
                credits = credits_init if is_abusive else credits_init + credits_inc
                _db.cur.execute(
                    "UPDATE user SET watched_time=? WHERE plex_id=?",
                    (watched_time, plex_id),
                )
                if not is_abusive:
                    _db.cur.execute(
                        "UPDATE statistics SET credits=? WHERE tg_id=?", (credits, tg_id)
                    )
                    _handle_debt_after_credit_update(_db, tg_id, credits)

                if is_abusive:
                    notification_tasks.append((
                        tg_id,
                        f"⚠️ 今日观看时长异常 ({play_duration:.1f}h)，已超过合理阈值，本日积分已清零。如有疑问请联系管理员。",
                    ))
                    for chat_id in settings.TG_ADMIN_CHAT_ID:
                        notification_tasks.append((
                            chat_id,
                            f"🚨 异常观看告警：Plex 用户 {plex_username} (TG: {tg_id}) 今日观看 {play_duration:.1f}h，超过阈值 {ABUSE_THRESHOLD}h",
                        ))
                elif play_duration > 0:
                    bonus_line = _build_credit_bonus_lines(
                        dual_bind_multiplier, medal_multiplier
                    )
                    notification_tasks.append((
                        tg_id,
                        f"""
╭━━━━━━━━━━━━━━━━━━━━━━━━━╮
┃  🎬 Plex 每日观影报告  ┃
╰━━━━━━━━━━━━━━━━━━━━━━━━━╯

🌟 今日观看收益
━━━━━━━━━━━━━━━━━
   ⏱️  观看时长：{play_duration:.2f} 小时
   💎  基础积分：+{base_credits:.2f}
{bonus_line}   ✨  实际获得：+{credits_inc:.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━

💰 当前总积分：{credits:.2f}
🎞️  总观看时长：{watched_time:.2f} 小时

━━━━━━━━━━━━━━━━━━━━━━━━━
💜 MisayaMedia · 享受观影时光""",
                    ))

            logger.info(
                f"更新 Plex 用户 {plex_username} ({plex_id}) 的积分和观看时长: "
                f"新增观看时长 {round(play_duration, 2)} 小时，基础积分 {round(base_credits, 2)}，实际积分 {round(credits_inc, 2)}"
            )

    except Exception as e:
        logger.error(f"更新 Plex 用户积分及观看时长失败: {e}")
        for chat_id in settings.TG_ADMIN_CHAT_ID:
            notification_tasks.append(
                (
                    chat_id,
                    f"更新 Plex 用户积分及观看时长失败: {e}",
                )
            )
        return notification_tasks
    else:
        _db.con.commit()
        logger.info("Plex 用户积分及观看时长更新完成")
        return notification_tasks
    finally:
        _db.close()


def update_emby_credits():
    """更新 emby 积分及观看时长"""
    logger.info("开始更新 Emby 用户积分及观看时长")
    emby = Emby()
    _db = DB()
    notification_tasks = []
    try:
        _db.sync_checkin_total_rank_medals()
        duration = emby.get_user_total_play_time()
        users = _db.cur.execute(
            "select emby_id, tg_id, emby_watched_time, emby_credits, emby_username from emby_user"
        ).fetchall()
        ABUSE_THRESHOLD = settings.ABUSE_WATCH_THRESHOLD
        for user in users:
            emby_id, tg_id, watched_time, emby_credits_init, emby_username = user
            watched_time = watched_time or 0.0
            emby_credits_init = emby_credits_init or 0.0
            playduration = round(float(duration.get(emby_id, 0)) / 3600, 2)
            if playduration == 0:
                continue

            base_watch = max(0.0, round(playduration - watched_time, 2))

            # 双账号绑定加成
            if tg_id:
                has_plex = bool(_db.get_plex_info_by_tg_id(tg_id))
                dual_bind_multiplier = settings.DUAL_BIND_MULTIPLIER if has_plex else 1.0
                medal_multiplier = _db.get_user_medal_multiplier(tg_id)
            else:
                dual_bind_multiplier = 1.0
                medal_multiplier = 1.0
            multiplier = dual_bind_multiplier * medal_multiplier
            base_credits = min(base_watch, 8)
            credits_inc = round(base_credits * multiplier, 2)

            # 异常观看检测
            is_abusive = base_watch > ABUSE_THRESHOLD
            if is_abusive:
                credits_inc = 0

            if not tg_id:
                _credits = emby_credits_init + credits_inc
                _db.cur.execute(
                    "UPDATE emby_user SET emby_watched_time=?,emby_credits=? WHERE emby_id=?",
                    (playduration, _credits, emby_id),
                )
            else:
                stats_info = _db.get_stats_by_tg_id(tg_id)
                if stats_info:
                    credits_init = stats_info[2]
                    _credits = credits_init + credits_inc
                    _db.update_user_credits(_credits, tg_id=tg_id)
                    _handle_debt_after_credit_update(_db, tg_id, _credits)
                else:
                    _db.update_user_credits(0, emby_id=emby_id)
                    _credits = emby_credits_init + credits_inc
                    _db.add_user_data(tg_id, credits=_credits)
                _db.cur.execute(
                    "UPDATE emby_user SET emby_watched_time=? WHERE emby_id=?",
                    (playduration, emby_id),
                )

                if is_abusive:
                    notification_tasks.append((
                        tg_id,
                        f"⚠️ 今日 Emby 观看时长异常 ({base_watch:.1f}h)，已超过合理阈值，本日积分已清零。如有疑问请联系管理员。",
                    ))
                    for chat_id in settings.TG_ADMIN_CHAT_ID:
                        notification_tasks.append((
                            chat_id,
                            f"🚨 异常观看告警：Emby 用户 {emby_username} (TG: {tg_id}) 今日观看 {base_watch:.1f}h，超过阈值 {ABUSE_THRESHOLD}h",
                        ))
                elif base_watch > 0:
                    bonus_line = _build_credit_bonus_lines(
                        dual_bind_multiplier, medal_multiplier
                    )
                    notification_tasks.append((
                        tg_id,
                        f"""
╭━━━━━━━━━━━━━━━━━━━━━━━━━╮
┃  📺 Emby 每日观影报告  ┃
╰━━━━━━━━━━━━━━━━━━━━━━━━━╯

🌟 今日观看收益
━━━━━━━━━━━━━━━━━
   ⏱️  观看时长：{base_watch:.2f} 小时
   💎  基础积分：+{base_credits:.2f}
{bonus_line}   ✨  实际获得：+{credits_inc:.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━

💰 当前总积分：{_credits:.2f}
🎞️  总观看时长：{playduration:.2f} 小时

━━━━━━━━━━━━━━━━━━━━━━━━━
💜 MisayaMedia · 享受观影时光""",
                    ))

            logger.info(
                f"更新 Emby 用户 {emby_username} ({emby_id}) 的积分和观看时长: "
                f"新增观看时长 {base_watch:.2f} 小时，基础积分 {base_credits:.2f}，实际积分 {credits_inc:.2f}"
            )
    except Exception as e:
        logger.error(f"更新 Emby 用户积分及观看时长失败: {e}")
        for chat_id in settings.TG_ADMIN_CHAT_ID:
            notification_tasks.append(
                (
                    chat_id,
                    f"更新 Emby 用户积分及观看时长失败: {e}",
                )
            )
        return notification_tasks
    else:
        _db.con.commit()
        logger.info("Emby 用户积分及观看时长更新完成")
        return notification_tasks
    finally:
        _db.close()


async def update_credits():
    """更新 Plex 和 Emby 用户积分及观看时长"""
    logger.info("开始执行每日积分结算任务")
    notification_tasks = update_plex_credits()
    notification_tasks.extend(update_emby_credits())
    logger.info(f"准备发送 {len(notification_tasks)} 条通知")

    success_count = 0
    fail_count = 0

    for tg_id, text in notification_tasks:
        try:
            # 发送通知消息，使用静默模式避免打扰用户
            await send_message_by_url(chat_id=tg_id, text=text, disable_notification=True)
            success_count += 1
            logger.info(f"成功发送积分结算通知给用户 {tg_id}")
        except Exception as e:
            fail_count += 1
            logger.error(f"发送积分结算通知给用户 {tg_id} 失败: {str(e)}")
        await asyncio.sleep(1)

    logger.info(f"积分结算通知发送完成: 成功 {success_count} 条，失败 {fail_count} 条")


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
        # 检查是否存在 plex_id 为空的用户
        empty_plex_users = _db.cur.execute(
            "SELECT plex_email FROM user WHERE plex_id IS NULL"
        ).fetchall()
        for user in empty_plex_users:
            email = user[0]
            # 处理 plex_id 为空的用户
            plex_id = _plex.get_user_id_by_email(email)
            plex_username = _plex.get_username_by_user_id(plex_id) if plex_id else None
            if plex_id and plex_username:
                _db.cur.execute(
                    "UPDATE user SET plex_id=?, plex_username=? WHERE plex_email=?",
                    (plex_id, plex_username, email),
                )
            else:
                logger.warning(f"无法找到 Plex 用户 {email} 的 ID 或用户名，跳过更新。")
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
    更新捐赠积分

    Args:
        old_multiplier: 旧的积分倍数
        new_multiplier: 新的积分倍数
    """
    try:
        db = DB()
        # 获取所有捐赠记录
        donations = db.cur.execute(
            "SELECT tg_id, donation, credits FROM statistics WHERE donation > 0"
        ).fetchall()

        for tg_id, donation, credits in donations:
            # 计算新的积分
            new_credits = round(
                credits + donation * (new_multiplier - old_multiplier), 2
            )
            # 更新数据库
            db.cur.execute(
                "UPDATE statistics SET credits = ? WHERE tg_id = ?",
                (new_credits, tg_id),
            )
            logger.info(
                f"用户 {tg_id} 捐赠：{donation}, 更新积分: {credits} -> {new_credits}"
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
                code = generate_unique_invitation_code(db.invitation_code_exists)
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
                        f"添加邀请码 {code} 给用户 {get_user_name_from_tg_id(uid)}，有效期 {INVITATION_EXPIRE_DAYS} 天"
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
                f"恭喜你，竞拍 {autction['title']} 获胜！最终出价为 {autction['final_price']} 积分",
            )
            if not autction.get("credits_reduced", False):
                # 如果未扣除积分，通知管理员
                for chat_id in settings.TG_ADMIN_CHAT_ID:
                    await send_message_by_url(
                        chat_id=chat_id,
                        text=f"用户 {autction.get('winner_id')} 在竞拍 {autction['title']} 中获胜，但未扣除积分。",
                    )
        return finished_auctions
    except Exception as e:
        logger.error(f"自动结束过期竞拍失败: {e}")
    finally:
        db.close()


async def update_line_traffic_stats(
    count: int = settings.REDIS_LINE_TRAFFIC_STATS_HANDLE_SIZE,
):
    """消费 Redis 中的 HTTP 流量日志并写入排行榜统计表。"""
    values = stream_traffic_cache.redis_client.lpop(
        "filebeat_nginx_stream_logs", count=count
    )

    if not values:
        logger.info("没有新的流量日志数据")
        return 0

    _db = DB()
    processed_count = 0

    try:
        for raw_log in values:
            try:
                if isinstance(raw_log, bytes):
                    raw_log = raw_log.decode("utf-8")

                log_data = json.loads(raw_log)

                timestamp = log_data.get("@timestamp", "")
                service = (log_data.get("service") or "").strip().lower()
                request_uri = log_data.get("request_uri") or ""
                status_code = int(log_data.get("status") or 0)
                bytes_sent = int(log_data.get("bytes_sent") or 0)

                if not service or not request_uri:
                    continue
                if status_code < 200 or status_code >= 300:
                    continue
                # 过滤心跳、播放进度等极小请求
                if bytes_sent < 1024:
                    continue

                parsed_url = urlparse(request_uri)
                query_params = parse_qs(parsed_url.query)

                username = None
                user_id = None

                if service == "plex":
                    token_list = query_params.get("X-Plex-Token")
                    if not token_list:
                        continue

                    token = token_list[0]
                    cached_username = plex_token_cache.get(token)
                    if isinstance(cached_username, bytes):
                        cached_username = cached_username.decode("utf-8")
                    username = cached_username

                    if username:
                        user_result = _db.cur.execute(
                            "SELECT plex_id FROM user WHERE LOWER(plex_username)=?",
                            (username.lower(),),
                        ).fetchone()
                        if user_result:
                            user_id = user_result[0]
                    else:
                        try:
                            plex_url = (
                                f"{settings.PLEX_BASE_URL.strip('/')}/myplex/account"
                                f"?X-Plex-Token={token}"
                            )
                            response = httpx.get(plex_url, timeout=5.0)
                            if response.status_code != 200:
                                continue

                            import xml.etree.ElementTree as ET

                            root = ET.fromstring(response.text)
                            username = root.get("username")
                            if not username:
                                continue

                            plex_token_cache.put(token, username)
                            user_result = _db.cur.execute(
                                "SELECT plex_id FROM user WHERE LOWER(plex_username)=?",
                                (username.lower(),),
                            ).fetchone()
                            if user_result:
                                user_id = user_result[0]
                        except Exception as e:
                            logger.debug(f"通过 Plex Token 解析用户名失败: {e}")
                            continue

                elif service == "emby":
                    api_key_list = (
                        query_params.get("api_key")
                        or query_params.get("ApiKey")
                        or query_params.get("X-Emby-Token")
                    )
                    user_id_list = query_params.get("UserId")

                    if api_key_list:
                        token = api_key_list[0]
                        cached_username = emby_api_key_cache.get(token)
                        if isinstance(cached_username, bytes):
                            cached_username = cached_username.decode("utf-8")
                        username = cached_username

                        if username:
                            user_result = _db.cur.execute(
                                "SELECT emby_id FROM emby_user WHERE LOWER(emby_username)=?",
                                (username.lower(),),
                            ).fetchone()
                            if user_result:
                                user_id = user_result[0]
                        else:
                            try:
                                emby = Emby()
                                username = await emby.get_emby_username_from_api_key(
                                    token
                                )
                                if not username:
                                    continue

                                emby_api_key_cache.put(token, username)
                                user_result = _db.cur.execute(
                                    "SELECT emby_id FROM emby_user WHERE LOWER(emby_username)=?",
                                    (username.lower(),),
                                ).fetchone()
                                if user_result:
                                    user_id = user_result[0]
                            except Exception as e:
                                logger.debug(f"通过 Emby API Key 解析用户名失败: {e}")
                                continue
                    elif user_id_list:
                        emby_id = user_id_list[0]
                        user_result = _db.cur.execute(
                            "SELECT emby_username FROM emby_user WHERE emby_id=?",
                            (emby_id,),
                        ).fetchone()
                        if user_result:
                            username = user_result[0]
                            user_id = emby_id
                    else:
                        continue

                else:
                    continue

                if not username:
                    continue

                try:
                    formatted_timestamp = (
                        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        .astimezone(settings.TZ)
                        .isoformat()
                    )
                except (ValueError, AttributeError):
                    formatted_timestamp = datetime.now(settings.TZ).isoformat()

                if _db.create_line_traffic_entry(
                    line=f"http-{service}",
                    send_bytes=bytes_sent,
                    service=service,
                    username=username,
                    user_id=user_id,
                    timestamp=formatted_timestamp,
                ):
                    processed_count += 1

            except json.JSONDecodeError as e:
                logger.error(f"流量日志 JSON 解析失败: {e}")
            except Exception as e:
                logger.error(f"处理流量日志时出错: {e}")

        logger.info(f"成功处理了 {processed_count} 条流量日志")
        return processed_count
    except Exception as e:
        logger.error(f"更新线路流量统计时发生错误: {e}")
        return processed_count
    finally:
        _db.close()


async def update_traffic_stats_from_tautulli():
    """基于 Tautulli/Emby 观看时长为当天补录估算流量。"""
    logger.info("开始基于 Tautulli 观看时长估算流量数据")

    _db = DB()
    processed_count = 0
    average_bitrate_bytes_per_hour = int(3.6 * 1024 * 1024 * 1024)

    try:
        _plex = Plex()
        _tautulli = Tautulli()

        today_stats = _tautulli.get_home_stats(
            time_range=1,
            stats_type="duration",
            stats_count=len(_plex.users_by_id) + 50,
            stat_id="top_users",
        )
        if not today_stats:
            logger.warning("无法从 Tautulli 获取观看统计数据")
            return 0

        today_duration = get_user_total_duration(today_stats)
        plex_users = _db.cur.execute(
            "SELECT plex_id, plex_username, tg_id FROM user WHERE plex_id IS NOT NULL"
        ).fetchall()
        plex_user_map = {
            str(user[0]): {"username": user[1], "tg_id": user[2]} for user in plex_users
        }

        now = datetime.now(settings.TZ)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        existing_today = _db.cur.execute(
            """SELECT DISTINCT username FROM line_traffic_stats
               WHERE line = 'tautulli-estimate'
                 AND timestamp >= ?
                 AND service = 'plex'""",
            (today_start.isoformat(),),
        ).fetchall()
        existing_usernames = {row[0].lower() for row in existing_today if row[0]}

        for user_id, watch_hours in today_duration.items():
            if watch_hours <= 0:
                continue

            user_info = plex_user_map.get(str(user_id))
            if not user_info:
                continue

            username = user_info["username"]
            if not username or username.lower() in existing_usernames:
                continue

            estimated_bytes = int(watch_hours * average_bitrate_bytes_per_hour)
            success = _db.create_line_traffic_entry(
                line="tautulli-estimate",
                send_bytes=estimated_bytes,
                service="plex",
                username=username,
                user_id=str(user_id),
                timestamp=now.isoformat(),
            )
            if success:
                processed_count += 1

        try:
            emby_duration = Emby().get_user_total_play_time()
            emby_users = _db.cur.execute(
                """SELECT emby_id, emby_username, tg_id, emby_watched_time
                   FROM emby_user
                   WHERE emby_id IS NOT NULL"""
            ).fetchall()

            existing_emby_today = _db.cur.execute(
                """SELECT DISTINCT username FROM line_traffic_stats
                   WHERE line = 'tautulli-estimate'
                     AND timestamp >= ?
                     AND service = 'emby'""",
                (today_start.isoformat(),),
            ).fetchall()
            existing_emby_usernames = {
                row[0].lower() for row in existing_emby_today if row[0]
            }

            for emby_id, username, _tg_id, prev_watched_time in emby_users:
                if not username or username.lower() in existing_emby_usernames:
                    continue

                current_watch_seconds = float(emby_duration.get(emby_id, 0))
                current_watch_hours = current_watch_seconds / 3600

                if prev_watched_time and prev_watched_time > 0:
                    today_hours = max(0, current_watch_hours - prev_watched_time)
                else:
                    today_hours = min(current_watch_hours, 24)

                if today_hours <= 0:
                    continue

                estimated_bytes = int(today_hours * average_bitrate_bytes_per_hour)
                success = _db.create_line_traffic_entry(
                    line="tautulli-estimate",
                    send_bytes=estimated_bytes,
                    service="emby",
                    username=username,
                    user_id=str(emby_id),
                    timestamp=now.isoformat(),
                )
                if success:
                    processed_count += 1
        except Exception as e:
            logger.warning(f"处理 Emby 流量估算时出错: {e}")

        logger.info(f"基于 Tautulli 估算流量完成，共处理 {processed_count} 条记录")
        return processed_count
    except Exception as e:
        logger.error(f"基于 Tautulli 估算流量时发生错误: {e}")
        return processed_count
    finally:
        _db.close()


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
            # 未接受邀请，此时数据库中的 plex_id 为空
            if not user[0]:
                continue
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


def write_user_info_cache():
    """
    将 user info 写入 redis 缓存
    """
    _db = DB()
    try:
        # 获取 Plex 用户信息
        plex_users = _db.cur.execute(
            "SELECT plex_id, tg_id, plex_username, plex_email FROM user"
        ).fetchall()
        for user in plex_users:
            plex_id = user[0]
            # 未接受邀请，此时数据库中的 plex_id 为空
            if not plex_id:
                continue
            tg_id = user[1]
            plex_username = user[2]
            plex_email = user[3]
            if plex_username:
                user_info_cache.put(
                    f"plex:{plex_username.lower()}",
                    json.dumps(
                        {
                            "plex_id": plex_id,
                            "tg_id": tg_id,
                            "plex_username": plex_username,
                            "plex_email": plex_email,
                        }
                    ),
                )
        # 获取 Emby 用户信息
        emby_users = _db.cur.execute(
            "SELECT emby_id, tg_id, emby_username FROM emby_user"
        ).fetchall()
        for user in emby_users:
            emby_id = user[0]
            tg_id = user[1]
            emby_username = user[2]
            if emby_username:
                user_info_cache.put(
                    f"emby:{emby_username.lower()}",
                    json.dumps(
                        {
                            "emby_id": emby_id,
                            "tg_id": tg_id,
                            "emby_username": emby_username,
                        }
                    ),
                )
    except Exception as e:
        logger.error(f"写入用户信息缓存时发生错误: {e}")
    finally:
        _db.close()


async def check_user_in_group(tg_id: int, group_id: str) -> bool:
    """检查用户是否在群组中

    Args:
        tg_id: 用户的Telegram ID
        group_id: 群组ID

    Returns:
        bool: True表示在群组中，False表示不在
    """
    try:
        url = f"https://api.telegram.org/bot{settings.TG_API_TOKEN}/getChatMember"
        params = {"chat_id": group_id, "user_id": tg_id}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            data = response.json()

            if data.get("ok"):
                status = data.get("result", {}).get("status")
                # 在群组中的状态：member, administrator, creator
                return status in ["member", "administrator", "creator"]
            else:
                # API调用失败，保守起见返回True（避免误删）
                logger.warning(f"检查用户 {tg_id} 群组状态失败: {data.get('description')}")
                return True
    except Exception as e:
        logger.error(f"检查用户 {tg_id} 是否在群组时出错: {e}")
        return True  # 出错时保守返回True


async def process_left_group_members():
    """检查所有用户的群组状态，处理不在群组超过72小时的用户

    工作流程：
    1. 检查所有已绑定Plex/Emby的用户是否在群组中
    2. 对于不在群组的用户，记录首次检测时间
    3. 每24小时发送一次警告通知（24小时、48小时）
    4. 在72小时时注销账号并发送通知
    """
    logger.info("开始检查用户群组状态")
    _db = DB()
    notification_tasks = []

    # 检查是否配置了群组ID
    if not settings.TG_GROUP:
        logger.warning("未配置TG_GROUP，跳过群组检查")
        return

    try:
        # 获取所有绑定了Plex或Emby的用户
        # 从 user 表获取 Plex 用户
        plex_users = _db.cur.execute(
            """
            SELECT DISTINCT tg_id FROM user
            WHERE tg_id IS NOT NULL AND plex_id IS NOT NULL
            """
        ).fetchall()

        # 从 emby_user 表获取 Emby 用户
        emby_users = _db.cur.execute(
            """
            SELECT DISTINCT tg_id FROM emby_user
            WHERE tg_id IS NOT NULL AND emby_id IS NOT NULL
            """
        ).fetchall()

        # 合并去重
        all_tg_ids = set()
        for user in plex_users:
            all_tg_ids.add(user["tg_id"])
        for user in emby_users:
            all_tg_ids.add(user["tg_id"])

        if not all_tg_ids:
            logger.info("没有需要检查的用户")
            return

        logger.info(f"开始检查 {len(all_tg_ids)} 个用户的群组状态 (Plex用户: {len(plex_users)}, Emby用户: {len(emby_users)})")

        # 获取管理员和特权用户ID列表
        admin_ids = [int(admin_id) for admin_id in settings.TG_ADMIN_CHAT_ID]
        privileged_user_ids = settings.TG_PRIVILEGED_USERS

        for tg_id in all_tg_ids:
            # 跳过管理员和特权用户
            if tg_id in admin_ids or tg_id in privileged_user_ids:
                continue

            # 检查用户是否在群组中
            is_in_group = await check_user_in_group(tg_id, settings.TG_GROUP)

            if is_in_group:
                # 用户在群组中，清除离开记录（如果有）
                existing_record = _db.cur.execute(
                    "SELECT * FROM group_member_left_status WHERE tg_id = ?",
                    (tg_id,)
                ).fetchone()

                if existing_record:
                    _db.remove_group_member_left_record(tg_id)
                    logger.info(f"用户 {tg_id} 已在群组中，清除离开记录")
            else:
                # 用户不在群组中，处理离开记录
                await handle_user_not_in_group(tg_id, _db, notification_tasks)

            # 避免API请求过快
            await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"检查用户群组状态时发生错误: {e}")
    finally:
        _db.close()

    # 发送所有通知
    if notification_tasks:
        await asyncio.gather(*notification_tasks, return_exceptions=True)

    logger.info("用户群组状态检查完成")


async def handle_user_not_in_group(tg_id: int, _db: DB, notification_tasks: list):
    """处理不在群组的用户

    工作流程：
    - 首次检测：创建离开记录
    - 24小时：发送第一次警告
    - 48小时：发送第二次警告
    - 72小时：发送最后警告并注销账号

    Args:
        tg_id: 用户ID
        _db: 数据库连接
        notification_tasks: 通知任务列表
    """
    current_time = int(time())

    # 检查是否已有离开记录
    existing_record = _db.cur.execute(
        "SELECT * FROM group_member_left_status WHERE tg_id = ?",
        (tg_id,)
    ).fetchone()

    if not existing_record:
        # 首次检测到不在群组，创建记录
        _db.add_group_member_left_record(
            tg_id=tg_id,
            left_time=current_time,
            group_id=int(settings.TG_GROUP)
        )
        logger.info(f"用户 {tg_id} 不在群组中，已创建离开记录")
        return

    # 已有记录，检查离开时长
    left_time = existing_record["left_time"]
    time_elapsed = current_time - left_time
    hours_elapsed = time_elapsed // 3600  # 转换为小时
    is_processed = existing_record["is_processed"]

    # 获取最后一次警告时间
    try:
        last_warning_time = existing_record["last_warning_time"]
    except (KeyError, IndexError):
        last_warning_time = 0

    # 计算距离上次警告的时间（小时）
    hours_since_last_warning = (current_time - last_warning_time) // 3600 if last_warning_time > 0 else 999

    logger.info(f"用户 {tg_id} 离开群组已 {hours_elapsed} 小时")

    # 72小时以上：注销账号
    if hours_elapsed >= 72 and not is_processed:
        await deactivate_user_accounts(tg_id, _db, notification_tasks)
    # 24小时周期发送警告（24小时、48小时时发送）
    elif hours_elapsed >= 24 and not is_processed and hours_since_last_warning >= 24:
        username = get_user_name_from_tg_id(tg_id)
        remaining_hours = 72 - hours_elapsed

        warning_msg = (
            f"⚠️ 群组加入提醒 ⚠️\n\n"
            f"检测到您未加入指定群组！\n\n"
            f"已离开时间：{hours_elapsed} 小时\n"
            f"剩余时间：{remaining_hours} 小时\n\n"
            f"您的账号将在 {remaining_hours} 小时后被自动注销。\n"
            f"请尽快加入群组以保留您的账号：\n\n"
            f"群组链接：{settings.TG_GROUP_LINK if hasattr(settings, 'TG_GROUP_LINK') and settings.TG_GROUP_LINK else '请联系管理员获取'}\n\n"
            f"如已加入群组，请忽略此消息。"
        )
        notification_tasks.append(
            send_message_by_url(chat_id=tg_id, text=warning_msg)
        )
        # 更新最后警告时间
        _db.mark_left_member_warning_sent(tg_id)
        logger.info(f"已向用户 {tg_id} ({username}) 发送警告通知（离开 {hours_elapsed} 小时）")


async def deactivate_user_accounts(tg_id: int, _db: DB, notification_tasks: list):
    """注销用户的Plex/Emby账号

    Args:
        tg_id: 用户ID
        _db: 数据库连接
        notification_tasks: 通知任务列表
    """
    try:
        # 获取用户信息
        plex_info = _db.get_plex_info_by_tg_id(tg_id)
        emby_info = _db.get_emby_info_by_tg_id(tg_id)

        if not plex_info and not emby_info:
            logger.info(f"用户 {tg_id} 未绑定Plex/Emby账号，跳过")
            _db.mark_left_member_as_processed(tg_id)
            return

        # 获取用户名用于通知
        username = get_user_name_from_tg_id(tg_id)
        deactivated_services = []

        # 处理Plex账号
        if plex_info:
            plex_id = plex_info[0]
            plex_username = plex_info[4]

            try:
                _plex = Plex()
                success, msg = _plex.remove_friend(plex_id)

                if success:
                    _db.delete_plex_user(tg_id)
                    deactivated_services.append("Plex")
                    logger.info(f"成功注销用户 {username} (ID: {tg_id}) 的Plex账号: {plex_username}")
                else:
                    logger.error(f"删除Plex好友失败: {username} (ID: {tg_id}), {msg}")
            except Exception as e:
                logger.error(f"处理Plex账号时出错: {username} (ID: {tg_id}), {e}")

        # 处理Emby账号
        if emby_info:
            emby_id = emby_info[1]
            emby_username = emby_info[0]

            try:
                _emby = Emby()
                success, msg = _emby.delete_user(emby_id)

                if success:
                    _db.delete_emby_user(tg_id)
                    deactivated_services.append("Emby")
                    logger.info(f"成功注销用户 {username} (ID: {tg_id}) 的Emby账号: {emby_username}")
                else:
                    logger.error(f"删除Emby用户失败: {username} (ID: {tg_id}), {msg}")
            except Exception as e:
                logger.error(f"处理Emby账号时出错: {username} (ID: {tg_id}), {e}")

        # 发送注销通知
        if deactivated_services:
            services_text = " 和 ".join(deactivated_services)
            notification_msg = (
                f"⚠️ 账号注销通知\n\n"
                f"用户：{username}\n"
                f"由于您未加入指定群组超过72小时，您的 {services_text} 账号已被自动注销。\n\n"
                f"如需恢复账号，请加入群组并联系管理员。\n"
                f"群组链接：{settings.TG_GROUP_LINK if hasattr(settings, 'TG_GROUP_LINK') and settings.TG_GROUP_LINK else '请联系管理员获取'}"
            )
            notification_tasks.append(
                send_message_by_url(chat_id=tg_id, text=notification_msg)
            )

        # 标记为已处理
        _db.mark_left_member_as_processed(tg_id)

    except Exception as e:
        logger.error(f"注销用户 {tg_id} 账号时发生错误: {e}")



def _handle_debt_after_credit_update(db, tg_id: int, new_credits: float) -> None:
    """积分更新后处理债务状态：转正则清零 debt_since"""
    if new_credits >= 0:
        db.clear_debt_since(tg_id)


async def check_debt_and_ban():
    """检查欠积分超过 DEBT_MAX_MONTHS 个月的用户并封禁"""
    import time as _time
    from datetime import datetime as _dt
    logger.info("开始检查欠积分超期用户...")
    _db = DB()
    notification_tasks = []
    try:
        debtors = _db.get_all_debtors()
        max_seconds = settings.DEBT_MAX_MONTHS * 30 * 86400
        now = int(_time.time())

        for row in debtors:
            tg_id, credits, debt_since = row["tg_id"], row["credits"], row["debt_since"]
            if not debt_since:
                continue

            age_days = (now - debt_since) // 86400
            remaining_days = max(0, settings.DEBT_MAX_MONTHS * 30 - age_days)

            # 提前 7 天警告
            if remaining_days == 7:
                notification_tasks.append((
                    tg_id,
                    (
                        "⚠️ 欠积分催缴警告\n\n"
                        f"您的账号积分为 {credits:.1f}（欠款），"
                        f"距离账号封禁还剩 7 天。\n"
                        "请尽快通过观看内容补充积分，以避免账号被注销。"
                    )))
                continue

            if now - debt_since < max_seconds:
                continue

            # 超期 → 封禁：删除 Plex/Emby 账号
            username = _db.get_stats_by_tg_id(tg_id)
            plex_info = _db.get_plex_info_by_tg_id(tg_id)
            emby_info = _db.get_emby_info_by_tg_id(tg_id)
            deactivated = []

            if plex_info:
                try:
                    from app.plex import Plex
                    ok, _ = Plex().remove_friend(plex_info[0])
                    if ok:
                        _db.delete_plex_user(tg_id)
                        deactivated.append("Plex")
                except Exception as e:
                    logger.error(f"封禁 Plex 失败 tg_id={tg_id}: {e}")

            if emby_info:
                try:
                    from app.emby import Emby
                    ok, _ = Emby().delete_user(emby_info[1])
                    if ok:
                        _db.delete_emby_user(tg_id)
                        deactivated.append("Emby")
                except Exception as e:
                    logger.error(f"封禁 Emby 失败 tg_id={tg_id}: {e}")

            if deactivated:
                logger.info(f"已封禁欠积分用户 tg_id={tg_id}，注销服务: {deactivated}")
                _db.clear_debt_since(tg_id)
                services_text = " 和 ".join(deactivated)
                notification_tasks.append((
                    tg_id,
                    (
                        "🚫 账号封禁通知\n\n"
                        f"由于您的积分长期为负（当前 {credits:.1f}），"
                        f"已超过 {settings.DEBT_MAX_MONTHS} 个月未能还清欠款，"
                        f"您的 {services_text} 账号已被自动注销。\n\n"
                        "如需恢复，请联系管理员。"
                    )))
                for admin_id in settings.TG_ADMIN_CHAT_ID:
                    notification_tasks.append((
                        admin_id,
                        f"🚨 欠积分封禁: 用户 {tg_id} 积分 {credits:.1f}，"
                        f"已欠款 {age_days} 天，注销: {services_text}"
                    ))
    except Exception as e:
        logger.error(f"债务检查失败: {e}")
    finally:
        _db.close()

    for tg_id, text in notification_tasks:
        try:
            await send_message_by_url(chat_id=tg_id, text=text)
        except Exception as e:
            logger.error(f"发送债务通知失败 tg_id={tg_id}: {e}")


async def settle_checkin_monthly():
    """每月1日：结算上月签到排行，前3名奖励积分"""
    logger.info("开始执行月度签到结算...")
    _db = DB()
    notification_tasks = []
    try:
        today = datetime.now(settings.TZ).date()
        # 结算上个月
        if today.month == 1:
            last_month = f"{today.year - 1}-12"
        else:
            last_month = f"{today.year}-{today.month - 1:02d}"

        rows = _db.get_checkin_monthly_leaderboard(last_month)
        reward = settings.CHECKIN_MONTHLY_TOP3_REWARD
        for i, row in enumerate(rows[:3]):
            tg_id = row["tg_id"]
            days = row["days"]
            stats = _db.get_stats_by_tg_id(tg_id)
            if stats:
                new_credits = round((stats["credits"] or 0) + reward, 2)
                _db.update_user_credits(new_credits, tg_id=tg_id)
                rank_emoji = ["🥇", "🥈", "🥉"][i]
                notification_tasks.append((
                    tg_id,
                    (
                        f"{rank_emoji} 月度签到奖励\n\n"
                        f"恭喜您在 {last_month} 月签到排行中位列第 {i+1} 名！\n"
                        f"本月签到 <b>{days} 天</b>，获得奖励 <b>+{reward:.0f} 积分</b>！\n"
                        f"当前积分：{new_credits:.2f}"
                    )))
        logger.info(f"月度签到结算完成，本月奖励 {min(3, len(rows))} 人")
    except Exception as e:
        logger.error(f"月度签到结算失败: {e}")
    finally:
        _db.close()

    for tg_id, text in notification_tasks:
        try:
            await send_message_by_url(chat_id=tg_id, text=text)
        except Exception as e:
            logger.error(f"发送月度奖励通知失败: {e}")


if __name__ == "__main__":
    update_plex_credits()
    update_plex_info()
    # add_all_plex_user()
    update_emby_credits()
    # 测试流量统计更新
    # update_line_traffic_stats()
