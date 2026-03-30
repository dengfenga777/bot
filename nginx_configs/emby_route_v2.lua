-- Emby智能路由脚本 v2
-- 根据Emby用户ID查询Redis，获取用户绑定的线路
-- 同时设置正确的proxy Host header

local redis = require "resty.redis"

-- IP到域名的映射（用于设置正确的Host header）
local IP_TO_DOMAIN = {
    ["154.3.36.75:443"] = "hk.stream.misaya.org",
    ["143.42.64.122:443"] = "sg.stream.misaya.org",
    ["154.31.114.167:443"] = "jp.stream.misaya.org",
    ["45.12.134.98:443"] = "us.stream.misaya.org",
}

-- 默认配置
local DEFAULT_BACKEND = "127.0.0.1:8096"
local DEFAULT_HOST = nil  -- 本地不需要特殊Host
local DEFAULT_PROTOCOL = "http"

local function get_user_route()
    -- 尝试从多个位置获取Emby用户ID
    local user_id = ngx.var.arg_UserId or
                    ngx.var.arg_userid or
                    ngx.var.arg_api_key

    -- 如果URL参数中没有，尝试从请求头获取
    if not user_id or user_id == "" then
        user_id = ngx.req.get_headers()["X-Emby-Token"]
    end

    -- 如果没有用户ID，返回默认配置
    if not user_id or user_id == "" then
        ngx.log(ngx.INFO, "Emby: 未找到用户ID，使用本地")
        return DEFAULT_BACKEND, DEFAULT_HOST, DEFAULT_PROTOCOL
    end

    -- 连接Redis
    local red = redis:new()
    red:set_timeout(1000) -- 1秒超时

    local ok, err = red:connect("127.0.0.1", 6379)
    if not ok then
        ngx.log(ngx.ERR, "Emby: Redis连接失败: ", err)
        return DEFAULT_BACKEND, DEFAULT_HOST, DEFAULT_PROTOCOL
    end

    -- 查询用户绑定的线路
    local line, err = red:get("emby_line:" .. user_id)

    -- 保持连接池
    red:set_keepalive(10000, 100)

    -- 如果Redis中没有记录，使用本地
    if not line or line == ngx.null then
        ngx.log(ngx.INFO, "Emby: 用户 ", user_id, " 未绑定线路，使用本地")
        return DEFAULT_BACKEND, DEFAULT_HOST, DEFAULT_PROTOCOL
    end

    -- 查找对应的域名
    local domain = IP_TO_DOMAIN[line]
    if domain then
        ngx.log(ngx.INFO, "Emby: 用户 ", user_id, " -> VPS ", line, " (", domain, ")")
        return line, domain, "https"
    else
        -- 未知的VPS IP，直接使用（可能是本地IP）
        ngx.log(ngx.INFO, "Emby: 用户 ", user_id, " -> ", line)
        return line, nil, "http"
    end
end

-- 执行路由
local backend, proxy_host, protocol = get_user_route()

-- 设置变量供Nginx使用
ngx.var.backend_addr = protocol .. "://" .. backend
if proxy_host then
    ngx.var.proxy_host = proxy_host
else
    ngx.var.proxy_host = ngx.var.host
end
