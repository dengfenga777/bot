local redis = require "resty.redis"
local http = require "resty.http"
local cjson = require "cjson.safe"
local route_common = require "common_route"

local REDIS_HOST = route_common.getenv("REDIS_HOST", "127.0.0.1")
local REDIS_PORT = tonumber(route_common.getenv("REDIS_PORT", "6379"))
local PLEX_SERVER = route_common.getenv("PLEX_LOCAL_ORIGIN", "http://127.0.0.1:32400")
local PLEX_PUBLIC_HOST = route_common.getenv("PLEX_PUBLIC_HOST", "plex.misaya.org")
local PLEX_ADMIN_TOKEN = route_common.getenv("PLEX_API_TOKEN", "")

local token_cache = ngx.shared.plex_token_cache

local function connect_redis()
    local red = redis:new()
    red:set_timeout(1000)

    local ok, err = red:connect(REDIS_HOST, REDIS_PORT)
    if not ok then
        ngx.log(ngx.ERR, "[Plex] Redis 连接失败: ", err)
        return nil
    end

    return red
end

local function get_plex_request_token()
    local headers = ngx.req.get_headers()
    return ngx.var.arg_X_Plex_Token
        or ngx.var.arg_x_plex_token
        or headers["X-Plex-Token"]
end

local function get_username_by_token_match(user_token)
    if not PLEX_ADMIN_TOKEN or PLEX_ADMIN_TOKEN == "" then
        ngx.log(ngx.WARN, "[Plex] 未配置 PLEX_API_TOKEN，回退本地入口")
        return nil
    end

    if token_cache then
        local cached = token_cache:get(user_token)
        if cached then
            return cached
        end
    end

    local httpc = http.new()
    httpc:set_timeout(5000)

    local res, err = httpc:request_uri(PLEX_SERVER .. "/accounts", {
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
    local accounts = data
        and data.MediaContainer
        and data.MediaContainer.Account

    if not accounts then
        ngx.log(ngx.WARN, "[Plex] /accounts 未返回账户列表")
        return nil
    end

    for _, account in ipairs(accounts) do
        local account_id = account.id
        local account_name = account.name

        if account_id and account_name then
            local account_res = httpc:request_uri(PLEX_SERVER .. "/accounts/" .. account_id, {
                method = "GET",
                headers = {
                    ["X-Plex-Token"] = PLEX_ADMIN_TOKEN,
                    ["Accept"] = "application/json",
                },
            })

            if account_res and account_res.status == 200 then
                local account_data = cjson.decode(account_res.body)
                local account_list = account_data
                    and account_data.MediaContainer
                    and account_data.MediaContainer.Account
                local account_info = account_list and account_list[1] or nil

                if account_info and account_info.authToken == user_token then
                    if token_cache then
                        token_cache:set(user_token, account_name, 3600)
                    end
                    return account_name
                end
            end
        end
    end

    return nil
end

local function get_route_target()
    local token = get_plex_request_token()
    if not token or token == "" then
        return nil
    end

    local username = get_username_by_token_match(token)
    if not username or username == "" then
        ngx.log(ngx.INFO, "[Plex] 无法定位用户名，使用本地入口")
        return nil
    end

    local red = connect_redis()
    if not red then
        return nil
    end

    local key = "plex_email:" .. username
    local target, err = red:get(key)
    red:set_keepalive(10000, 100)

    if err then
        ngx.log(ngx.ERR, "[Plex] 读取 Redis 失败 key=", key, " error=", err)
        return nil
    end

    if not target or target == ngx.null or target == "" then
        return nil
    end

    ngx.log(ngx.INFO, "[Plex] 用户 ", username, " -> ", target)
    return tostring(target)
end

local backend_addr, proxy_host = route_common.resolve_upstream(
    get_route_target(),
    PLEX_SERVER,
    PLEX_PUBLIC_HOST
)

ngx.var.backend_addr = backend_addr
ngx.var.proxy_host = proxy_host
