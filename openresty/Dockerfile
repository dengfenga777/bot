FROM openresty/openresty:alpine-fat

RUN /usr/local/openresty/bin/opm get ledgetech/lua-resty-http

COPY openresty/nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY openresty/conf.d /etc/openresty/conf.d
COPY openresty/lua /etc/openresty/lua

CMD ["openresty", "-g", "daemon off;"]
