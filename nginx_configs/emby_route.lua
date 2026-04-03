-- Emby智能路由脚本
-- 根据Emby用户ID查询Redis，获取用户绑定的线路

local redis = require "resty.redis"

local function extract_host(target)
    if not target or target == "" then
        return ""
    end
    return string.match(target, "^([^:]+)") or ""
end

local function get_user_line()
    -- 尝试从多个位置获取Emby用户ID
    local user_id = ngx.var.arg_UserId or
                    ngx.var.arg_userid or
                    ngx.var.arg_api_key

    -- 如果URL参数中没有，尝试从请求头获取
    if not user_id or user_id == "" then
        user_id = ngx.req.get_headers()["X-Emby-Token"]
    end

    -- 空值表示由 Nginx 回退到本地默认入口
    local default_line = ""

    -- 如果没有用户ID，返回默认线路
    if not user_id or user_id == "" then
        ngx.log(ngx.INFO, "Emby: 未找到用户ID，使用默认线路")
        return default_line
    end

    -- 连接Redis
    local red = redis:new()
    red:set_timeout(1000) -- 1秒超时

    local ok, err = red:connect("127.0.0.1", 6379)
    if not ok then
        ngx.log(ngx.ERR, "Emby: Redis连接失败: ", err)
        return default_line
    end

    -- 查询用户绑定的线路
    -- 键格式: emby_line:<emby_id>
    local line, err = red:get("emby_line:" .. user_id)

    -- 如果Redis中没有记录，使用默认线路
    if not line or line == ngx.null then
        ngx.log(ngx.INFO, "Emby: 用户 ", user_id, " 未绑定线路，使用默认")
        line = default_line
    else
        ngx.log(ngx.INFO, "Emby: 用户 ", user_id, " -> 线路 ", line)
    end

    -- 保持连接池
    red:set_keepalive(10000, 100)

    return line
end

-- 设置后端服务器变量
ngx.var.backend_server = get_user_line()
ngx.var.backend_ssl_name = extract_host(ngx.var.backend_server)
