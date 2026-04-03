local route_common = require "common_route"

local PLEX_SERVER = route_common.getenv("PLEX_LOCAL_ORIGIN", "http://127.0.0.1:32400")
local PLEX_PUBLIC_HOST = route_common.getenv("PLEX_PUBLIC_HOST", "plex.misaya.org")

local ok, err = route_common.verify_request_signature("plex", PLEX_PUBLIC_HOST)
if not ok then
    ngx.log(ngx.WARN, "[PlexOrigin] 拒绝未授权请求: ", err or "unknown")
    return ngx.exit(ngx.HTTP_FORBIDDEN)
end

ngx.var.backend_addr = PLEX_SERVER
ngx.var.proxy_host = PLEX_PUBLIC_HOST
