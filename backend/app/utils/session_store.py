"""
Session 会话存储模块

使用 Lua 脚本保证 Redis 操作的原子性，与 Java 版本保持一致。
实现双结构存储：ZSet 索引 + Session 键值对。
"""

import json
import time

from redis.asyncio import Redis

from app.core.settings import Settings

# ==================== Lua 脚本定义 ====================

# 保存会话的 Lua 脚本
# 与 Java 版 login_limit.lua 保持一致
# KEYS[1]: indexKey (用户的 ZSet 索引)
# KEYS[2]: sessionKey (会话键)
# ARGV[1]: maxLoginNum (最大登录数)
# ARGV[2]: score (时间戳分数)
# ARGV[3]: currentSession (会话 JSON)
# ARGV[4]: ttlSec (过期秒数)
SAVE_SESSION_SCRIPT = """
local indexKey       = KEYS[1]
local sessionKey     = KEYS[2]
local maxLoginNum    = tonumber(ARGV[1])
local score          = tonumber(ARGV[2])
local currentSession = ARGV[3]
local ttlSec         = tonumber(ARGV[4])
local delCmd         = ARGV[5] or "UNLINK"

-- 参数校验
if (not maxLoginNum or not score or not ttlSec) then
    return redis.error_reply("ARGV参数错误")
end

-- 获取全部 token，清理已过期的 session
local total = redis.call("ZRANGE", indexKey, "0", "-1")
local expiredMember = {}
local chunk = 1000

for i = 1, #total, 1 do
    local value = redis.call("GET", total[i])
    -- 如果 session 已过期（GET 返回 nil），加入过期集合
    if (not value) then
        expiredMember[#expiredMember + 1] = total[i]
    end
end

-- 分批删除 ZSet 中过期的元素
for i = 1, #expiredMember, chunk do
    local last = math.min(#expiredMember, i + chunk - 1)
    redis.call("ZREM", indexKey, unpack(expiredMember, i, last))
end

-- 向 ZSet 中添加当前会话
redis.call("ZADD", indexKey, score, sessionKey)
redis.call("EXPIRE", indexKey, ttlSec)

-- 存储会话数据
redis.call("SET", sessionKey, currentSession, "EX", ttlSec)

-- 检查并限制最大登录数
local currentLoginNum = redis.call("ZCARD", indexKey)
local member = {}

if currentLoginNum > maxLoginNum then
    local over = currentLoginNum - maxLoginNum
    local poped = redis.call("ZPOPMIN", indexKey, over)
    
    if poped and #poped > 0 then
        -- ZPOPMIN 返回 {member1, score1, member2, score2, ...}
        for i = 1, #poped, 2 do
            member[#member + 1] = poped[i]
        end
        -- 分批删除被踢出的会话
        for i = 1, #member, chunk do
            local last = math.min(#member, i + chunk - 1)
            redis.call(delCmd, unpack(member, i, last))
        end
    end
end

return #member
"""

# 删除会话的 Lua 脚本
# KEYS[1]: sessionKey
# KEYS[2]: indexKey
REMOVE_SESSION_SCRIPT = """
local sessionKey = KEYS[1]
local indexKey   = KEYS[2]

redis.call("DEL", sessionKey)
redis.call("ZREM", indexKey, sessionKey)

return 1
"""


class SessionStore:
    """
    封装 Redis 会话存取逻辑。

    使用 Lua 脚本保证操作原子性，与 Java 版本的键格式和逻辑一致。
    支持最大登录数限制，超出时踢掉最早的会话。
    """

    def __init__(self, redis: Redis, settings: Settings):
        self.redis = redis
        self.settings = settings
        # 注册 Lua 脚本（只在首次调用时发送到 Redis）
        self._save_script = None
        self._remove_script = None

    def session_key(self, user_id: str, token: str) -> str:
        """
        生成会话键，格式: agent:user:{userId}:session:{token}
        """
        return f"agent:user:{{{user_id}}}:session:{token}"

    def index_key(self, user_id: str) -> str:
        """
        生成 ZSet 索引键，存放用户所有会话。
        格式: agent:user:{userId}
        """
        return f"agent:user:{{{user_id}}}"

    async def _get_save_script(self):
        """延迟初始化保存脚本"""
        if self._save_script is None:
            self._save_script = self.redis.register_script(SAVE_SESSION_SCRIPT)
        return self._save_script

    async def _get_remove_script(self):
        """延迟初始化删除脚本"""
        if self._remove_script is None:
            self._remove_script = self.redis.register_script(REMOVE_SESSION_SCRIPT)
        return self._remove_script

    async def save_session(self, payload: dict, ttl_seconds: int, max_login_num: int = 3) -> int:
        """
        保存会话到 Redis（原子操作）。

        1. 清理已过期的会话索引
        2. 添加新会话到 ZSet 和 String
        3. 如果超过最大登录数，踢掉最早的会话

        Args:
            payload: 会话数据，必须包含 id 和 token
            ttl_seconds: 过期时间（秒）
            max_login_num: 用户允许的最大登录数（来自用户配置）

        Returns:
            被踢掉的会话数量
        """
        user_id = str(payload.get("id"))
        token = payload.get("token", "")
        session_key = self.session_key(user_id, token)
        index_key = self.index_key(user_id)
        session_json = json.dumps(payload, ensure_ascii=False)
        now_ms = int(time.time() * 1000)

        # 执行 Lua 脚本
        script = await self._get_save_script()
        kicked_count = await script(
            keys=[index_key, session_key],
            args=[max_login_num, now_ms, session_json, ttl_seconds, "UNLINK"],
        )
        return kicked_count

    async def load_session(self, user_id: str, token: str) -> dict | None:
        """
        读取并解析会话，不存在返回 None。
        """
        session_key = self.session_key(user_id, token)
        raw = await self.redis.get(session_key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def remove_session(self, user_id: str, token: str) -> None:
        """
        删除会话（原子操作）。

        同时删除会话数据和 ZSet 索引。
        """
        session_key = self.session_key(user_id, token)
        index_key = self.index_key(user_id)

        # 执行 Lua 脚本
        script = await self._get_remove_script()
        await script(keys=[session_key, index_key])

    async def get_user_sessions(self, user_id: str) -> list[str]:
        """
        获取用户所有活跃会话的 token 列表。

        用于查看用户当前的登录设备数。
        """
        index_key = self.index_key(user_id)
        session_keys = await self.redis.zrange(index_key, 0, -1)
        # 从 session_key 中提取 token
        tokens = []
        for key in session_keys:
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            # 格式: agent:user:{userId}:session:{token}
            if ":session:" in key:
                token = key.split(":session:")[-1]
                tokens.append(token)
        return tokens
