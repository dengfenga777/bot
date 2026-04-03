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

return M
