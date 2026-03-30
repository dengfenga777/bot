from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class Card(BaseModel):
    """扑克牌"""
    suit: str = Field(..., description="花色（♠♥♣♦）")
    rank: str = Field(..., description="牌面（A/2-10/J/Q/K）")
    value: int = Field(..., description="点数值")


class GameStatus(str, Enum):
    """游戏状态"""
    BETTING = "betting"  # 下注阶段
    PLAYING = "playing"  # 玩家回合
    DEALER_TURN = "dealer_turn"  # 庄家回合
    FINISHED = "finished"  # 游戏结束


class GameResult(str, Enum):
    """游戏结果"""
    WIN = "win"  # 玩家赢
    LOSE = "lose"  # 玩家输
    PUSH = "push"  # 平局
    BLACKJACK = "blackjack"  # 21点（天生黑杰克）
    BUST = "bust"  # 爆牌
    DEALER_BUST = "dealer_bust"  # 庄家爆牌


class BlackjackConfig(BaseModel):
    """21点游戏配置"""
    min_bet: int = Field(default=10, ge=1, description="最小下注积分")
    max_bet: int = Field(default=1000, ge=1, description="最大下注积分")
    min_credits_required: int = Field(default=50, ge=1, description="最低积分要求")
    blackjack_payout_ratio: float = Field(default=1.5, ge=1.0, description="黑杰克赔率")
    win_payout_ratio: float = Field(default=1.0, ge=0.5, description="普通赢赔率")
    enabled: bool = Field(default=True, description="游戏是否开放")


class BlackjackConfigUpdateRequest(BaseModel):
    """更新21点配置请求"""
    min_bet: Optional[int] = Field(None, ge=1, description="最小下注积分")
    max_bet: Optional[int] = Field(None, ge=1, description="最大下注积分")
    min_credits_required: Optional[int] = Field(None, ge=1, description="最低积分要求")
    blackjack_payout_ratio: Optional[float] = Field(None, ge=1.0, description="黑杰克赔率")
    win_payout_ratio: Optional[float] = Field(None, ge=0.5, description="普通赢赔率")
    enabled: Optional[bool] = Field(None, description="游戏是否开放")


class StartGameRequest(BaseModel):
    """开始游戏请求"""
    bet_amount: int = Field(..., ge=1, description="下注金额")


class GameActionRequest(BaseModel):
    """游戏操作请求"""
    game_id: str = Field(..., description="游戏ID")


class BlackjackGameState(BaseModel):
    """21点游戏状态"""
    game_id: str = Field(..., description="游戏ID")
    user_id: int = Field(..., description="玩家ID")
    bet_amount: int = Field(..., description="下注金额")
    player_hand: List[Card] = Field(default=[], description="玩家手牌")
    dealer_hand: List[Card] = Field(default=[], description="庄家手牌")
    player_score: int = Field(default=0, description="玩家点数")
    dealer_score: int = Field(default=0, description="庄家点数")
    game_status: GameStatus = Field(default=GameStatus.BETTING, description="游戏状态")
    result: Optional[GameResult] = Field(None, description="游戏结果")
    credits_change: float = Field(default=0.0, description="积分变化")
    current_credits: float = Field(default=0.0, description="当前积分")
    dealer_hidden_card: bool = Field(default=True, description="庄家是否有暗牌")


class BlackjackStats(BaseModel):
    """21点统计数据"""
    total_games: int = Field(default=0, description="总游戏局数")
    total_wins: int = Field(default=0, description="玩家总赢次数")
    total_losses: int = Field(default=0, description="玩家总输次数")
    total_pushes: int = Field(default=0, description="平局次数")
    total_blackjacks: int = Field(default=0, description="黑杰克次数")
    total_bet_amount: float = Field(default=0.0, description="总下注金额")
    total_payout_amount: float = Field(default=0.0, description="总赔付金额")
    house_edge: float = Field(default=0.0, description="庄家优势")
    active_players: int = Field(default=0, description="活跃玩家数")
    today_games: int = Field(default=0, description="今日游戏局数")
    week_games: int = Field(default=0, description="本周游戏局数")
