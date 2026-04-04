local http = require "resty.http"
local redis = require "resty.redis"
local route_common = require "common_route"

local REDIS_HOST = route_common.getenv("REDIS_HOST", "127.0.0.1")
local REDIS_PORT = tonumber(route_common.getenv("REDIS_PORT", "6379"))
local PLEX_SERVER = route_common.getenv("PLEX_LOCAL_ORIGIN", "http://127.0.0.1:32400")
local PLEX_PUBLIC_HOST = route_common.getenv("PLEX_PUBLIC_HOST", "plex.misaya.org")
local PLEX_ADMIN_TOKEN = route_common.getenv("PLEX_API_TOKEN", "")

local token_cache = ngx.shared.plex_token_cache

local function get_request_arg(args, ...)
    for i = 1, select("#", ...) do
        local name = select(i, ...)
        local value = args[name]
        if type(value) == "table" then
            value = value[1]
        end
        if value and value ~= "" then
            return value
        end
    end
    return nil
end

local function normalize_identity(value)
    if not value or value == "" then
        return nil
    end

    local normalized = string.lower((tostring(value):gsub("^%s+", ""):gsub("%s+$", "")))
    if normalized == "" then
        return nil
    end

    return normalized
end

local function get_token_cache_value(kind, user_token)
    if not token_cache or not user_token or user_token == "" then
        return nil
    end

    local cached = token_cache:get(kind .. ":" .. user_token)
    if cached and cached ~= "" then
        return cached
    end

    return nil
end

local function set_token_cache_value(kind, user_token, value)
    local normalized_value = normalize_identity(value)
    if not token_cache or not user_token or user_token == "" or not normalized_value then
        return
    end

    token_cache:set(kind .. ":" .. user_token, normalized_value, 3600)
end

local function parse_xml_attributes(attr_text)
    local attrs = {}
    if not attr_text or attr_text == "" then
        return attrs
    end

    for key, value in tostring(attr_text):gmatch('([%w_:%-]+)="([^"]*)"') do
        attrs[key] = value
    end

    return attrs
end

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

local function read_route_target_from_redis(key)
    local red = connect_redis()
    if not red then
        return nil
    end

    local target, err = red:get(key)
    red:set_keepalive(10000, 100)

    if err then
        ngx.log(ngx.ERR, "[Plex] 读取 Redis 失败 key=", key, " error=", err)
        return nil
    end

    if not target or target == ngx.null or target == "" then
        return nil
    end

    return tostring(target)
end

local function get_plex_request_token()
    local headers = ngx.req.get_headers()
    local args = ngx.req.get_uri_args()
    return get_request_arg(
        args,
        "X-Plex-Token",
        "x-plex-token",
        "X_Plex_Token",
        "x_plex_token"
    )
        or headers["X-Plex-Token"]
        or headers["x-plex-token"]
end

local function get_plex_request_identity_hint()
    local headers = ngx.req.get_headers()
    local args = ngx.req.get_uri_args()
    return normalize_identity(
        get_request_arg(
            args,
            "X-Plex-Username",
            "x-plex-username",
            "X_Plex_Username",
            "x_plex_username",
            "X-Plex-User",
            "x-plex-user",
            "X_Plex_User",
            "x_plex_user"
        )
            or headers["X-Plex-Username"]
            or headers["x-plex-username"]
            or headers["X-Plex-User"]
            or headers["x-plex-user"]
    )
end

local function resolve_identity_from_myplex_account(user_token)
    if not user_token or user_token == "" then
        return nil
    end

    local cached_username = get_token_cache_value("username", user_token)
    local cached_email = get_token_cache_value("email", user_token)
    local cached_title = get_token_cache_value("title", user_token)

    if cached_username or cached_email or cached_title then
        return cached_username or cached_email or cached_title, cached_username, cached_email
    end

    local httpc = http.new()
    httpc:set_timeout(5000)

    local res, err = httpc:request_uri(
        PLEX_SERVER
            .. "/myplex/account?X-Plex-Token="
            .. ngx.escape_uri(user_token),
        {
            method = "GET",
            headers = {
                ["X-Plex-Token"] = user_token,
                ["Accept"] = "application/xml",
            },
        }
    )

    if not res then
        ngx.log(ngx.ERR, "[Plex] /myplex/account 请求失败: ", err)
        return nil
    end

    if res.status ~= 200 then
        ngx.log(ngx.WARN, "[Plex] /myplex/account 返回状态: ", res.status)
        return nil
    end

    local response_body = res.body or ""
    local username = normalize_identity(response_body:match('username="([^"]+)"'))
    local email = normalize_identity(response_body:match('email="([^"]+)"'))
    local title = normalize_identity(response_body:match('title="([^"]+)"'))

    if username then
        set_token_cache_value("username", user_token, username)
    end
    if email then
        set_token_cache_value("email", user_token, email)
    end
    if title then
        set_token_cache_value("title", user_token, title)
    end

    return username or email or title, username, email
end

local function get_request_stream_part_id()
    local request_uri = ngx.var.uri or ""
    return request_uri:match("/library/parts/(%d+)/")
end

local function get_request_stream_rating_key()
    local args = ngx.req.get_uri_args()
    local path = get_request_arg(args, "path", "X-Plex-Path", "x-plex-path")
    if type(path) == "table" then
        path = path[1]
    end

    path = path or ngx.var.uri or ""
    return tostring(path):match("/library/metadata/(%d+)")
end

local function match_session_block_to_request(block, request_part_id, request_rating_key)
    if not block or block == "" then
        return false
    end

    if request_part_id and request_part_id ~= "" then
        if block:find('/library/parts/' .. request_part_id .. '/', 1, true) then
            return true
        end
        if block:find('<Part ', 1, true)
            and block:find(' id="' .. request_part_id .. '"', 1, true)
        then
            return true
        end
    end

    if request_rating_key and request_rating_key ~= "" then
        local open_tag_attrs = block:match("^<Video%s+(.-)>") or ""
        local attrs = parse_xml_attributes(open_tag_attrs)
        if attrs.ratingKey == request_rating_key then
            return true
        end
        if block:find('/library/metadata/' .. request_rating_key, 1, true) then
            return true
        end
    end

    return false
end

local function resolve_account_id_from_active_sessions(user_token)
    if not user_token or user_token == "" then
        return nil
    end

    local cached_account_id = get_token_cache_value("account_id", user_token)
    if cached_account_id then
        return cached_account_id
    end

    if not PLEX_ADMIN_TOKEN or PLEX_ADMIN_TOKEN == "" then
        return nil
    end

    local request_part_id = get_request_stream_part_id()
    local request_rating_key = get_request_stream_rating_key()
    if not request_part_id and not request_rating_key then
        return nil
    end

    local httpc = http.new()
    httpc:set_timeout(5000)

    local res, err = httpc:request_uri(
        PLEX_SERVER
            .. "/status/sessions?X-Plex-Token="
            .. ngx.escape_uri(PLEX_ADMIN_TOKEN),
        {
            method = "GET",
            headers = {
                ["Accept"] = "application/xml",
            },
        }
    )

    if not res then
        ngx.log(ngx.ERR, "[Plex] /status/sessions 请求失败: ", err)
        return nil
    end

    if res.status ~= 200 then
        ngx.log(ngx.WARN, "[Plex] /status/sessions 返回状态: ", res.status)
        return nil
    end

    local response_body = res.body or ""
    for block in response_body:gmatch("(<Video.-</Video>)") do
        if match_session_block_to_request(block, request_part_id, request_rating_key) then
            local account_id = normalize_identity(block:match('accountID="([^"]+)"'))
            if account_id then
                set_token_cache_value("account_id", user_token, account_id)
                ngx.log(
                    ngx.INFO,
                    "[Plex] 活动会话命中 account_id=",
                    account_id,
                    " part_id=",
                    request_part_id or "-",
                    " rating_key=",
                    request_rating_key or "-"
                )
                return account_id
            end
        end
    end

    return nil
end

local function find_route_target_by_identity(identity)
    local normalized_identity = normalize_identity(identity)
    if not normalized_identity then
        return nil
    end

    local key = "plex_email:" .. normalized_identity
    local target = read_route_target_from_redis(key)
    if target then
        ngx.log(ngx.INFO, "[Plex] 标识 ", normalized_identity, " -> ", target)
    end
    return target
end

local function find_route_target_by_account_id(account_id)
    local normalized_account_id = normalize_identity(account_id)
    if not normalized_account_id then
        return nil
    end

    local key = "plex_id:" .. normalized_account_id
    local target = read_route_target_from_redis(key)
    if target then
        ngx.log(ngx.INFO, "[Plex] account_id ", normalized_account_id, " -> ", target)
    end
    return target
end

local function get_route_target()
    local token = get_plex_request_token()
    local lookup_candidates = {}
    local seen = {}

    local function add_lookup_candidate(value)
        local normalized_value = normalize_identity(value)
        if not normalized_value or seen[normalized_value] then
            return
        end
        seen[normalized_value] = true
        table.insert(lookup_candidates, normalized_value)
    end

    add_lookup_candidate(get_plex_request_identity_hint())

    local account_identity, account_username, account_email =
        resolve_identity_from_myplex_account(token)
    add_lookup_candidate(account_identity)
    add_lookup_candidate(account_username)
    add_lookup_candidate(account_email)

    for _, identity in ipairs(lookup_candidates) do
        local target = find_route_target_by_identity(identity)
        if target then
            return target
        end
    end

    local account_id = resolve_account_id_from_active_sessions(token)
    if account_id then
        local target = find_route_target_by_account_id(account_id)
        if target then
            return target
        end
        ngx.log(ngx.INFO, "[Plex] account_id 未匹配共享线路: ", account_id)
    end

    if #lookup_candidates == 0 then
        ngx.log(ngx.INFO, "[Plex] 无法定位用户标识，使用本地入口")
    else
        ngx.log(
            ngx.INFO,
            "[Plex] 用户标识未匹配共享线路: ",
            table.concat(lookup_candidates, ",")
        )
    end

    return nil
end

local is_stream_request = route_common.is_plex_stream_request()
local route_target = nil

if is_stream_request then
    route_target = get_route_target()
end

local effective_target = route_target

if is_stream_request
    and route_common.is_domain_target(route_target, PLEX_PUBLIC_HOST)
then
    local redirect_url, err = route_common.build_client_redirect_url(
        "plex",
        ngx.var.host,
        route_target,
        { request_method = ngx.req.get_method() }
    )
    if redirect_url then
        ngx.log(
            ngx.INFO,
            "[Plex] 播放请求重定向到共享线路 host=",
            route_common.extract_host(route_target) or "unknown",
            " uri=",
            ngx.var.uri or "/"
        )
        return ngx.redirect(redirect_url, ngx.HTTP_TEMPORARY_REDIRECT)
    end

    ngx.log(ngx.WARN, "[Plex] 构建共享线路重定向失败: ", err or "unknown")
    effective_target = nil
elseif not is_stream_request then
    -- Plex 控制面保持走主入口，仅在真正的播放/转码请求上切换到共享线路。
    effective_target = nil
end

route_common.attach_request_signature("plex", ngx.var.host)

local backend_addr, proxy_host = route_common.resolve_upstream(
    effective_target,
    PLEX_SERVER,
    PLEX_PUBLIC_HOST
)

ngx.var.backend_addr = backend_addr
ngx.var.proxy_host = proxy_host
