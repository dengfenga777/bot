import json
import random
import secrets
import time
from typing import List

from app.cache import redis_cache, blackjack_game_state_cache
from app.db import DB
from app.log import logger
from app.utils.utils import get_user_name_from_tg_id
from app.webapp.auth import get_telegram_user
from app.webapp.middlewares import require_telegram_auth
from app.webapp.routers.admin import check_admin_permission
from app.webapp.schemas import TelegramUser
from app.webapp.schemas.blackjack import (
    BlackjackConfig,
    BlackjackConfigUpdateRequest,
    BlackjackGameState,
    BlackjackStats,
    Card,
    GameActionRequest,
    GameResult,
    GameStatus,
    StartGameRequest,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/blackjack", tags=["21点游戏"])

# 默认游戏配置
DEFAULT_BLACKJACK_CONFIG = BlackjackConfig(
    min_bet=10,
    max_bet=1000,
    min_credits_required=50,
    blackjack_payout_ratio=1.5,
    win_payout_ratio=1.0,
    enabled=True,
)

# 扑克牌花色和牌面
SUITS = ["♠", "♥", "♣", "♦"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]


def get_blackjack_config() -> BlackjackConfig:
    """获取21点配置"""
    try:
        config_str = redis_cache.get("blackjack:config")
        if config_str:
            config_dict = json.loads(config_str)
            return BlackjackConfig(**config_dict)
        else:
            # 如果没有配置，使用默认配置并保存到Redis
            save_blackjack_config(DEFAULT_BLACKJACK_CONFIG)
            return DEFAULT_BLACKJACK_CONFIG
    except Exception as e:
        logger.error(f"获取21点配置失败: {e}")
        return DEFAULT_BLACKJACK_CONFIG


def save_blackjack_config(config: BlackjackConfig):
    """保存21点配置到Redis"""
    try:
        config_json = config.model_dump_json()
        redis_cache.put("blackjack:config", config_json)
        logger.info("21点配置已保存到Redis")
    except Exception as e:
        logger.error(f"保存21点配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="保存配置失败"
        )


def create_deck() -> List[Card]:
    """创建一副扑克牌"""
    deck = []
    for suit in SUITS:
        for rank in RANKS:
            # 计算牌的点数
            if rank == "A":
                value = 11  # A初始为11，计算总分时会调整
            elif rank in ["J", "Q", "K"]:
                value = 10
            else:
                value = int(rank)

            deck.append(Card(suit=suit, rank=rank, value=value))

    return deck


def shuffle_deck(deck: List[Card]) -> List[Card]:
    """洗牌"""
    # 使用安全的随机数生成器
    secure_random = secrets.SystemRandom()
    shuffled = deck.copy()
    secure_random.shuffle(shuffled)
    return shuffled


def calculate_hand_value(hand: List[Card]) -> int:
    """计算手牌点数"""
    total = sum(card.value for card in hand)
    aces = sum(1 for card in hand if card.rank == "A")

    # 如果有A且总分超过21，将A从11改为1
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total


def is_blackjack(hand: List[Card]) -> bool:
    """判断是否是黑杰克（天生21点）"""
    return len(hand) == 2 and calculate_hand_value(hand) == 21


def generate_game_id(user_id: int) -> str:
    """生成游戏ID"""
    timestamp = int(time.time() * 1000)
    random_part = secrets.token_hex(4)
    return f"{user_id}_{timestamp}_{random_part}"


def save_game_state(game_state: BlackjackGameState):
    """保存游戏状态到Redis"""
    try:
        game_json = game_state.model_dump_json()
        # 游戏状态保存30分钟（通过 blackjack_game_state_cache 的 ttl_seconds 设置）
        blackjack_game_state_cache.put(game_state.game_id, game_json)
    except Exception as e:
        logger.error(f"保存游戏状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="保存游戏状态失败"
        )


def get_game_state(game_id: str) -> BlackjackGameState:
    """从Redis获取游戏状态"""
    try:
        game_str = blackjack_game_state_cache.get(game_id)
        if not game_str:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="游戏不存在或已过期"
            )
        game_dict = json.loads(game_str)
        return BlackjackGameState(**game_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取游戏状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取游戏状态失败"
        )


def delete_game_state(game_id: str):
    """删除游戏状态"""
    try:
        blackjack_game_state_cache.delete(game_id)
    except Exception as e:
        logger.error(f"删除游戏状态失败: {e}")


@router.get("/config", response_model=BlackjackConfig)
async def get_config():
    """获取21点配置"""
    try:
        config = get_blackjack_config()
        return config
    except Exception as e:
        logger.error(f"获取21点配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取配置失败"
        )


@router.put("/config")
@require_telegram_auth
async def update_config(
    request: Request,
    config_update_request: BlackjackConfigUpdateRequest,
    current_user: TelegramUser = Depends(get_telegram_user),
):
    """更新21点配置（仅管理员）"""
    try:
        # 检查管理员权限
        check_admin_permission(current_user)

        # 获取当前配置
        current_config = get_blackjack_config()

        # 更新配置
        update_data = config_update_request.model_dump(exclude_none=True)
        for key, value in update_data.items():
            setattr(current_config, key, value)

        # 验证配置合理性
        if current_config.min_bet > current_config.max_bet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="最小下注不能大于最大下注",
            )

        # 保存配置
        save_blackjack_config(current_config)

        logger.info(
            f"管理员 {get_user_name_from_tg_id(current_user.id)} 更新了21点配置"
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"message": "21点配置更新成功"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新21点配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新配置失败"
        )


@router.post("/start", response_model=BlackjackGameState)
@require_telegram_auth
async def start_game(
    request: Request,
    start_request: StartGameRequest,
    current_user: TelegramUser = Depends(get_telegram_user),
):
    """开始新游戏"""
    try:
        db = DB()
        user_id = current_user.id

        # 获取配置
        config = get_blackjack_config()

        # 检查游戏是否开放
        if not config.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="21点游戏暂未开放"
            )

        # 验证下注金额
        bet_amount = start_request.bet_amount
        if bet_amount < config.min_bet or bet_amount > config.max_bet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"下注金额必须在 {config.min_bet} 到 {config.max_bet} 之间",
            )

        # 获取用户当前积分
        flag, current_credits = db.get_user_credits(user_id)
        if not flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=current_credits
            )

        # 检查积分是否足够
        if current_credits < config.min_credits_required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"积分不足，需要至少 {config.min_credits_required} 积分才能参与",
            )

        if current_credits < bet_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"积分不足，当前积分: {current_credits}",
            )

        # 扣除下注积分
        new_credits = current_credits - bet_amount
        db.update_user_credits(credits=new_credits, tg_id=user_id)

        # 创建并洗牌
        deck = create_deck()
        deck = shuffle_deck(deck)

        # 发牌：玩家2张，庄家2张
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        # 计算初始点数
        player_score = calculate_hand_value(player_hand)
        dealer_score = calculate_hand_value(dealer_hand)

        # 生成游戏ID
        game_id = generate_game_id(user_id)

        # 创建游戏状态
        game_state = BlackjackGameState(
            game_id=game_id,
            user_id=user_id,
            bet_amount=bet_amount,
            player_hand=player_hand,
            dealer_hand=dealer_hand,
            player_score=player_score,
            dealer_score=dealer_score,
            game_status=GameStatus.PLAYING,
            current_credits=new_credits,
            dealer_hidden_card=True,
        )

        # 检查是否天生黑杰克
        if is_blackjack(player_hand):
            if is_blackjack(dealer_hand):
                # 双方都是黑杰克，平局
                game_state.result = GameResult.PUSH
                game_state.credits_change = 0
                game_state.current_credits = new_credits + bet_amount
            else:
                # 玩家黑杰克，赢
                game_state.result = GameResult.BLACKJACK
                payout = bet_amount * config.blackjack_payout_ratio
                game_state.credits_change = payout
                game_state.current_credits = new_credits + bet_amount + payout

            game_state.game_status = GameStatus.FINISHED
            game_state.dealer_hidden_card = False

            # 更新玩家积分
            db.update_user_credits(credits=game_state.current_credits, tg_id=user_id)

            # 记录游戏结果到数据库
            db.add_blackjack_game_record(
                user_id=user_id,
                bet_amount=bet_amount,
                result=game_state.result.value,
                credits_change=game_state.credits_change,
                player_score=player_score,
                dealer_score=dealer_score,
            )

        # 保存游戏状态
        save_game_state(game_state)

        logger.info(
            f"用户 {get_user_name_from_tg_id(user_id)} 开始21点游戏，下注: {bet_amount}"
        )

        return game_state

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"开始游戏失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="开始游戏失败"
        )
    finally:
        db.close()


@router.post("/hit", response_model=BlackjackGameState)
@require_telegram_auth
async def hit_card(
    request: Request,
    action_request: GameActionRequest,
    current_user: TelegramUser = Depends(get_telegram_user),
):
    """要牌"""
    try:
        db = DB()
        user_id = current_user.id

        # 获取游戏状态
        game_state = get_game_state(action_request.game_id)

        # 验证游戏归属
        if game_state.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此游戏"
            )

        # 验证游戏状态
        if game_state.game_status != GameStatus.PLAYING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="游戏已结束或状态异常"
            )

        # 创建新牌并发给玩家
        deck = create_deck()
        deck = shuffle_deck(deck)
        new_card = deck.pop()
        game_state.player_hand.append(new_card)
        game_state.player_score = calculate_hand_value(game_state.player_hand)

        # 检查是否爆牌
        if game_state.player_score > 21:
            game_state.game_status = GameStatus.FINISHED
            game_state.result = GameResult.BUST
            game_state.credits_change = -game_state.bet_amount
            game_state.dealer_hidden_card = False

            # 记录游戏结果
            db.add_blackjack_game_record(
                user_id=user_id,
                bet_amount=game_state.bet_amount,
                result=game_state.result.value,
                credits_change=game_state.credits_change,
                player_score=game_state.player_score,
                dealer_score=game_state.dealer_score,
            )

            # 删除游戏状态
            delete_game_state(game_state.game_id)
        else:
            # 继续游戏，保存状态
            save_game_state(game_state)

        logger.info(
            f"用户 {get_user_name_from_tg_id(user_id)} 要牌，当前点数: {game_state.player_score}"
        )

        return game_state

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"要牌失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="要牌失败"
        )
    finally:
        db.close()


@router.post("/stand", response_model=BlackjackGameState)
@require_telegram_auth
async def stand(
    request: Request,
    action_request: GameActionRequest,
    current_user: TelegramUser = Depends(get_telegram_user),
):
    """停牌（庄家回合）"""
    try:
        db = DB()
        user_id = current_user.id
        config = get_blackjack_config()

        # 获取游戏状态
        game_state = get_game_state(action_request.game_id)

        # 验证游戏归属
        if game_state.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此游戏"
            )

        # 验证游戏状态
        if game_state.game_status != GameStatus.PLAYING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="游戏已结束或状态异常"
            )

        # 庄家回合：庄家必须在17点及以上停牌
        game_state.game_status = GameStatus.DEALER_TURN
        game_state.dealer_hidden_card = False

        deck = create_deck()
        deck = shuffle_deck(deck)

        while game_state.dealer_score < 17:
            new_card = deck.pop()
            game_state.dealer_hand.append(new_card)
            game_state.dealer_score = calculate_hand_value(game_state.dealer_hand)

        # 判断胜负
        game_state.game_status = GameStatus.FINISHED

        if game_state.dealer_score > 21:
            # 庄家爆牌，玩家赢
            game_state.result = GameResult.DEALER_BUST
            payout = game_state.bet_amount * config.win_payout_ratio
            game_state.credits_change = payout
            game_state.current_credits += game_state.bet_amount + payout
        elif game_state.player_score > game_state.dealer_score:
            # 玩家点数更大，玩家赢
            game_state.result = GameResult.WIN
            payout = game_state.bet_amount * config.win_payout_ratio
            game_state.credits_change = payout
            game_state.current_credits += game_state.bet_amount + payout
        elif game_state.player_score < game_state.dealer_score:
            # 庄家点数更大，玩家输
            game_state.result = GameResult.LOSE
            game_state.credits_change = -game_state.bet_amount
        else:
            # 点数相同，平局
            game_state.result = GameResult.PUSH
            game_state.credits_change = 0
            game_state.current_credits += game_state.bet_amount

        # 更新玩家积分
        db.update_user_credits(credits=game_state.current_credits, tg_id=user_id)

        # 记录游戏结果到数据库
        db.add_blackjack_game_record(
            user_id=user_id,
            bet_amount=game_state.bet_amount,
            result=game_state.result.value,
            credits_change=game_state.credits_change,
            player_score=game_state.player_score,
            dealer_score=game_state.dealer_score,
        )

        # 删除游戏状态
        delete_game_state(game_state.game_id)

        logger.info(
            f"用户 {get_user_name_from_tg_id(user_id)} 停牌，结果: {game_state.result.value}, "
            f"积分变化: {game_state.credits_change}"
        )

        return game_state

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停牌失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="停牌失败"
        )
    finally:
        db.close()


@router.get("/user-status")
@require_telegram_auth
async def get_user_status(
    request: Request, current_user: TelegramUser = Depends(get_telegram_user)
):
    """获取用户游戏参与状态"""
    try:
        db = DB()
        user_id = current_user.id

        # 获取配置
        config = get_blackjack_config()

        # 获取用户当前积分
        flag, current_credits = db.get_user_credits(user_id)
        if not flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=current_credits
            )

        can_participate = (
            current_credits >= config.min_credits_required and config.enabled
        )

        return {
            "can_participate": can_participate,
            "current_credits": current_credits,
            "min_credits_required": config.min_credits_required,
            "min_bet": config.min_bet,
            "max_bet": config.max_bet,
            "enabled": config.enabled,
        }

    except Exception as e:
        logger.error(f"获取用户游戏状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取用户状态失败"
        )
    finally:
        db.close()


@router.get("/stats")
@require_telegram_auth
async def get_blackjack_statistics(
    request: Request, current_user: TelegramUser = Depends(get_telegram_user)
):
    """获取21点统计数据（仅管理员）"""
    try:
        # 检查管理员权限
        check_admin_permission(current_user)

        db = DB()
        stats = db.get_blackjack_stats()

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取21点统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取统计数据失败"
        )
    finally:
        if "db" in locals():
            db.close()


@router.get("/user-activity-stats")
@require_telegram_auth
async def get_user_activity_stats(
    request: Request, current_user: TelegramUser = Depends(get_telegram_user)
):
    """获取用户个人21点活动统计数据"""
    try:
        db = DB()
        user_id = current_user.id

        # 获取用户21点统计数据
        stats = db.get_user_blackjack_stats(user_id)

        return {"success": True, "data": stats}

    except Exception as e:
        logger.error(f"获取用户活动统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户活动统计失败",
        )
    finally:
        db.close()
