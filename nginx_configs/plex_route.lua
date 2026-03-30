-- Plex智能路由脚本
-- 根据用户 token 通过管理员接口查询用户名，再从 Redis 获取线路绑定
-- 使用 /accounts 接口获取 token -> username 映射

local redis = require "resty.redis"
local http = require "resty.http"
local cjson = require "cjson.safe"

-- 配置
local PLEX_ADMIN_TOKEN = "L96oVsXjP9iGMQAsxTP7"
local PLEX_SERVER = "127.0.0.1:32400"
local REDIS_HOST = "127.0.0.1"
local REDIS_PORT = 6379
local DEFAULT_LINE = ""  -- 空值表示使用本地/主域名直连

-- IP到域名的映射（用于日志显示）
local IP_TO_DOMAIN = {
    ["154.3.36.75:443"] = "hk.stream.misaya.org",
    ["213.35.105.166:443"] = "sg.stream.misaya.org",
    ["154.31.114.167:443"] = "jp.stream.misaya.org",
    ["146.235.219.32:443"] = "us.stream.misaya.org",
}

-- 缓存用户 token -> username 映射 (使用共享内存)
local token_cache = ngx.shared.plex_token_cache

-- 使用管理员 token 获取所有用户账户，建立 authToken -> username 映射
local function build_token_username_map()
    local httpc = http.new()
    httpc:set_timeout(5000)

    -- 调用 /accounts 获取所有共享用户
    local res, err = httpc:request_uri("http://" .. PLEX_SERVER .. "/accounts", {
        method = "GET",
        headers = {
            ["X-Plex-Token"] = PLEX_ADMIN_TOKEN,
            ["Accept"] = "application/json",
        },
    })

    if not res then
        ngx.log(ngx.ERR, "[Plex] /accounts 请求失败: ", err)
        return nil
    end

    if res.status ~= 200 then
        ngx.log(ngx.ERR, "[Plex] /accounts 返回状态: ", res.status)
        return nil
    end

    local data = cjson.decode(res.body)
    if not data then
        ngx.log(ngx.ERR, "[Plex] /accounts JSON 解析失败")
        return nil
    end

    local accounts = data.MediaContainer and data.MediaContainer.Account
    if not accounts then
        ngx.log(ngx.WARN, "[Plex] /accounts 未找到账户列表")
        return {}
    end

    -- 构建 id -> username 映射
    local id_to_username = {}
    for _, account in ipairs(accounts) do
        if account.id and account.name then
            id_to_username[tostring(account.id)] = account.name
            ngx.log(ngx.DEBUG, "[Plex] 账户映射: ", account.id, " -> ", account.name)
        end
    end

    return id_to_username
end

-- 通过当前活动会话查找用户名
local function get_username_from_sessions(user_token)
    local httpc = http.new()
    httpc:set_timeout(5000)

    -- 使用管理员 token 查询当前活动会话
    local res, err = httpc:request_uri("http://" .. PLEX_SERVER .. "/status/sessions", {
        method = "GET",
        headers = {
            ["X-Plex-Token"] = PLEX_ADMIN_TOKEN,
            ["Accept"] = "application/json",
        },
    })

    if not res then
        ngx.log(ngx.ERR, "[Plex] /status/sessions 请求失败: ", err)
        return nil
    end

    if res.status ~= 200 then
        ngx.log(ngx.ERR, "[Plex] /status/sessions 返回: ", res.status)
        return nil
    end

    local data = cjson.decode(res.body)
    if not data or not data.MediaContainer then
        return nil
    end

    -- 会话中包含 User 信息
    local metadata = data.MediaContainer.Metadata
    if metadata then
        for _, session in ipairs(metadata) do
            if session.User and session.User.title then
                -- 返回第一个找到的用户（如果请求中的 token 匹配）
                ngx.log(ngx.DEBUG, "[Plex] 活动会话用户: ", session.User.title)
            end
        end
    end

    return nil
end

-- 使用管理员 token 通过 /accounts/{id}/access 获取用户的 authToken
-- 然后与请求中的 token 比对
local function get_username_by_token_match(user_token)
    -- 先检查缓存
    if token_cache then
        local cached = token_cache:get(user_token)
        if cached then
            ngx.log(ngx.INFO, "[Plex] Token 缓存命中: ", cached)
            return cached
        end
    end

    -- 获取账户列表
    local httpc = http.new()
    httpc:set_timeout(5000)

    local res, err = httpc:request_uri("http://" .. PLEX_SERVER .. "/accounts", {
        method = "GET",
        headers = {
            ["X-Plex-Token"] = PLEX_ADMIN_TOKEN,
            ["Accept"] = "application/json",
        },
    })

    if not res or res.status ~= 200 then
        ngx.log(ngx.ERR, "[Plex] /accounts 失败")
        return nil
    end

    local data = cjson.decode(res.body)
    if not data then return nil end

    local accounts = data.MediaContainer and data.MediaContainer.Account
    if not accounts then return nil end

    -- 对每个账户，获取其 authToken 并比对
    for _, account in ipairs(accounts) do
        local account_id = account.id
        local account_name = account.name

        if account_id then
            -- 获取该账户的访问令牌
            local token_res, token_err = httpc:request_uri(
                "http://" .. PLEX_SERVER .. "/accounts/" .. account_id,
                {
                    method = "GET",
                    headers = {
                        ["X-Plex-Token"] = PLEX_ADMIN_TOKEN,
                        ["Accept"] = "application/json",
                    },
                }
            )

            if token_res and token_res.status == 200 then
                local token_data = cjson.decode(token_res.body)
                if token_data and token_data.MediaContainer and token_data.MediaContainer.Account then
                    local acc_info = token_data.MediaContainer.Account[1]
                    if acc_info and acc_info.authToken == user_token then
                        ngx.log(ngx.INFO, "[Plex] Token 匹配成功: ", account_name)
                        -- 缓存结果 (1小时)
                        if token_cache then
                            token_cache:set(user_token, account_name, 3600)
                        end
                        return account_name
                    end
                end
            end
        end
    end

    ngx.log(ngx.WARN, "[Plex] 未找到匹配的账户")
    return nil
end

-- 检查请求头中是否有用户名信息
local function get_username_from_headers()
    -- 某些 Plex 客户端会在请求中携带用户名
    local username = ngx.req.get_headers()["X-Plex-Username"]
    if username and username ~= "" then
        ngx.log(ngx.INFO, "[Plex] 从请求头获取用户名: ", username)
        return username
    end
    return nil
end

local function get_user_line()
    -- 尝试从多个位置获取 Plex token
    local token = ngx.var.arg_X_Plex_Token or
                  ngx.var.arg_x_plex_token or
                  ngx.req.get_headers()["X-Plex-Token"]

    -- 如果没有 token，返回默认线路
    if not token or token == "" then
        ngx.log(ngx.INFO, "[Plex] 未找到 token，使用默认线路")
        return DEFAULT_LINE
    end

    ngx.log(ngx.INFO, "[Plex] Token: ", string.sub(token, 1, 10), "...")

    -- 方法1: 从请求头获取用户名
    local username = get_username_from_headers()

    -- 方法2: 通过 token 匹配获取用户名
    if not username then
        username = get_username_by_token_match(token)
    end

    if not username then
        ngx.log(ngx.WARN, "[Plex] 无法获取用户名，使用默认线路")
        return DEFAULT_LINE
    end

    ngx.log(ngx.INFO, "[Plex] 用户名: ", username)

    -- 连接 Redis 查询用户绑定的线路
    local red = redis:new()
    red:set_timeout(1000)

    local ok, err = red:connect(REDIS_HOST, REDIS_PORT)
    if not ok then
        ngx.log(ngx.ERR, "[Plex] Redis 连接失败: ", err)
        return DEFAULT_LINE
    end

    -- 查询用户绑定的线路
    -- 键格式: plex_email:<username>
    local redis_key = "plex_email:" .. username
    local line, err = red:get(redis_key)

    -- 关闭连接
    red:set_keepalive(10000, 100)

    if not line or line == ngx.null then
        ngx.log(ngx.INFO, "[Plex] 用户 ", username, " 未绑定线路，使用默认")
        return DEFAULT_LINE
    end

    local domain = IP_TO_DOMAIN[line] or line
    ngx.log(ngx.INFO, "[Plex] 用户 ", username, " -> 线路 ", domain, " (", line, ")")

    return line
end

-- 设置后端服务器变量
local line = get_user_line()
if line == "" or line == nil then
    -- 空值或 nil 表示使用本地直连
    ngx.var.backend_server = "127.0.0.1:32400"
else
    ngx.var.backend_server = line
end
