local bit = require "bit"

local M = {}

local FALLBACK_IP_TO_DOMAIN = {
    ["154.3.36.75:443"] = "hk.stream.misaya.org",
    ["213.35.105.166:443"] = "sg.stream.misaya.org",
    ["143.42.64.122:443"] = "sg.stream.misaya.org",
    ["154.31.114.167:443"] = "jp.stream.misaya.org",
    ["146.235.219.32:443"] = "us.stream.misaya.org",
    ["45.12.134.98:443"] = "us.stream.misaya.org",
}

function M.getenv(name, default)
    local value = os.getenv(name)
    if value == nil or value == "" then
        return default
    end
    return value
end

function M.extract_host(target)
    if not target or target == "" then
        return nil
    end
    local host = target:match("^([^:]+)")
    if host and host ~= "" then
        return host
    end
    return nil
end

function M.parse_host_port(target)
    if not target or target == "" then
        return nil, nil
    end

    local host, port = target:match("^([^:]+):(%d+)$")
    if host and port then
        return host, tonumber(port)
    end

    host = target:match("^([^:]+)$")
    if host and host ~= "" then
        return host, 443
    end

    return nil, nil
end

function M.is_ipv4(host)
    if not host then
        return false
    end
    return host:match("^%d+%.%d+%.%d+%.%d+$") ~= nil
end

function M.is_loopback_or_local(host)
    return host == "127.0.0.1" or host == "localhost"
end

function M.resolve_upstream(target, default_origin, default_host)
    if not target or target == "" then
        return default_origin, default_host
    end

    local host, port = M.parse_host_port(target)
    if not host or not port then
        return default_origin, default_host
    end

    local mapped_domain = FALLBACK_IP_TO_DOMAIN[target]
    if mapped_domain then
        return "https://" .. target, mapped_domain
    end

    if M.is_loopback_or_local(host) then
        return default_origin, default_host
    end

    local scheme = (port == 443 or port == 8443) and "https" or "http"
    local proxy_host = M.is_ipv4(host) and host or host
    return scheme .. "://" .. host .. ":" .. tostring(port), proxy_host
end

local function get_request_header(headers, ...)
    for i = 1, select("#", ...) do
        local name = select(i, ...)
        local value = headers[name]
        if value and value ~= "" then
            return value
        end
    end
    return nil
end

local function get_signing_secret()
    local secret = M.getenv("MEDIA_ROUTE_SIGNING_SECRET", "")
    if secret ~= "" then
        return secret
    end

    secret = M.getenv("SESSION_SECRET_KEY", "")
    if secret ~= "" then
        return secret
    end

    return M.getenv("PLEX_API_TOKEN", "")
end

local function constant_time_equals(left, right)
    if not left or not right or #left ~= #right then
        return false
    end

    local diff = 0
    for index = 1, #left do
        diff = bit.bor(diff, bit.bxor(left:byte(index), right:byte(index)))
    end
    return diff == 0
end

function M.build_signature_payload(service, entry_host, timestamp, method, request_uri)
    return table.concat({
        service or "",
        entry_host or "",
        tostring(timestamp or ""),
        method or "",
        request_uri or "",
    }, "\n")
end

function M.sign_payload(secret, payload)
    return ngx.encode_base64(ngx.hmac_sha1(secret, payload), true)
end

function M.attach_request_signature(service, entry_host)
    local secret = get_signing_secret()
    if secret == "" then
        ngx.log(ngx.ERR, "[Route] 未配置签名密钥，origin 验签将无法工作")
        ngx.var.route_service = ""
        ngx.var.route_entry_host = ""
        ngx.var.route_timestamp = ""
        ngx.var.route_signature = ""
        return
    end

    local timestamp = tostring(ngx.time())
    local payload = M.build_signature_payload(
        service,
        entry_host,
        timestamp,
        ngx.req.get_method(),
        ngx.var.request_uri
    )

    ngx.var.route_service = service or ""
    ngx.var.route_entry_host = entry_host or ""
    ngx.var.route_timestamp = timestamp
    ngx.var.route_signature = M.sign_payload(secret, payload)
end

function M.verify_request_signature(expected_service, expected_entry_host)
    local secret = get_signing_secret()
    if secret == "" then
        return false, "签名密钥未配置"
    end

    local headers = ngx.req.get_headers()
    local service = get_request_header(headers, "X-PMS-Route-Service", "x-pms-route-service")
    local entry_host = get_request_header(headers, "X-PMS-Entry-Host", "x-pms-entry-host")
    local timestamp = get_request_header(headers, "X-PMS-Route-Timestamp", "x-pms-route-timestamp")
    local signature = get_request_header(headers, "X-PMS-Route-Signature", "x-pms-route-signature")

    if not service or not entry_host or not timestamp or not signature then
        return false, "缺少验签头"
    end

    if service ~= expected_service then
        return false, "服务标识不匹配"
    end

    if expected_entry_host and expected_entry_host ~= "" and entry_host ~= expected_entry_host then
        return false, "入口域名不匹配"
    end

    local ts_num = tonumber(timestamp)
    if not ts_num then
        return false, "时间戳无效"
    end

    local ttl = tonumber(M.getenv("MEDIA_ROUTE_SIGN_TTL", "90")) or 90
    if math.abs(ngx.time() - ts_num) > ttl then
        return false, "签名已过期"
    end

    local payload = M.build_signature_payload(
        service,
        entry_host,
        timestamp,
        ngx.req.get_method(),
        ngx.var.request_uri
    )
    local expected_signature = M.sign_payload(secret, payload)
    if not constant_time_equals(signature, expected_signature) then
        return false, "签名校验失败"
    end

    return true, nil
end

return M
