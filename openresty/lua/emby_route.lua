local redis = require "resty.redis"
local route_common = require "common_route"

local REDIS_HOST = route_common.getenv("REDIS_HOST", "127.0.0.1")
local REDIS_PORT = tonumber(route_common.getenv("REDIS_PORT", "6379"))
local EMBY_SERVER = route_common.getenv("EMBY_LOCAL_ORIGIN", "http://127.0.0.1:8096")
local EMBY_PUBLIC_HOST = route_common.getenv("EMBY_PUBLIC_HOST", "emby.misaya.org")

local function connect_redis()
    local red = redis:new()
    red:set_timeout(1000)

    local ok, err = red:connect(REDIS_HOST, REDIS_PORT)
    if not ok then
        ngx.log(ngx.ERR, "[Emby] Redis 连接失败: ", err)
        return nil
    end

    return red
end

local function get_emby_user_token()
    local headers = ngx.req.get_headers()
    return ngx.var.arg_UserId
        or ngx.var.arg_userid
        or ngx.var.arg_api_key
        or headers["X-Emby-Token"]
end

local function get_route_target()
    local user_id = get_emby_user_token()
    if not user_id or user_id == "" then
        return nil
    end

    local red = connect_redis()
    if not red then
        return nil
    end

    local key = "emby_line:" .. user_id
    local target, err = red:get(key)
    red:set_keepalive(10000, 100)

    if err then
        ngx.log(ngx.ERR, "[Emby] 读取 Redis 失败 key=", key, " error=", err)
        return nil
    end

    if not target or target == ngx.null or target == "" then
        return nil
    end

    ngx.log(ngx.INFO, "[Emby] 用户 ", user_id, " -> ", target)
    return tostring(target)
end

route_common.attach_request_signature("emby", ngx.var.host)

local backend_addr, proxy_host = route_common.resolve_upstream(
    get_route_target(),
    EMBY_SERVER,
    EMBY_PUBLIC_HOST
)

ngx.var.backend_addr = backend_addr
ngx.var.proxy_host = proxy_host
