local route_common = require "common_route"

local EMBY_SERVER = route_common.getenv("EMBY_LOCAL_ORIGIN", "http://127.0.0.1:8096")
local EMBY_PUBLIC_HOST = route_common.getenv("EMBY_PUBLIC_HOST", "emby.misaya.org")

local ok, err = route_common.verify_request_signature("emby", EMBY_PUBLIC_HOST)
if not ok then
    ngx.log(ngx.WARN, "[EmbyOrigin] 拒绝未授权请求: ", err or "unknown")
    return ngx.exit(ngx.HTTP_FORBIDDEN)
end

ngx.var.backend_addr = EMBY_SERVER
ngx.var.proxy_host = EMBY_PUBLIC_HOST
