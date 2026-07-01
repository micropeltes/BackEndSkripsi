mqtt confirm jalan, db error
VPS 45.126.43.35
PORT 1199

## Nginx WebSocket Proxy

Jika backend FastAPI diproxy lewat Nginx, pastikan header upgrade WebSocket ikut diteruskan:

```nginx
location ^~ /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```
