# Deployment Information — Day 14

## Public URL

https://agent-production-b103e56c.up.railway.app

## Platform và source

- Platform: Railway; project day14-agent; environment production; service agent.
- Source deploy: 06-lab-complete/, Dockerfile multi-stage, 2 Uvicorn worker.
- Redis: service Redis trong cùng project, có redis-volume. Agent dùng reference variable REDIS_URL=${{Redis.REDIS_URL}}.
- Deploy bằng `railway up . --path-as-root --service agent` từ thư mục Part 6.
- Deployment ID: 9141270b-cce8-4995-93e3-cfe71bea8999.

## Biến môi trường đã cấu hình

AGENT_API_KEY (secret, không ghi giá trị vào bài), REDIS_URL (reference), ENVIRONMENT=production, PORT=8000, RATE_LIMIT_PER_MINUTE=10, DAILY_BUDGET_USD=1, LOG_LEVEL=INFO.

Lab dùng mock LLM, không cần API key LLM thật. Chi phí trả về là chi phí mô phỏng, không phải hóa đơn Railway.

## Test commands và kết quả

Đặt BASE và dùng AGENT_API_KEY đã lưu trong Terminal cá nhân, không ghi key thật vào tài liệu:

```bash
export BASE="https://agent-production-b103e56c.up.railway.app"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -i -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"What is deployment?"}'
```

| Kiểm tra | HTTP | Nguồn bằng chứng |
|---|---:|---|
| GET /health | 200 | Codex gọi URL public, body {"status":"ok"} |
| GET /ready | 200 | Codex gọi URL public, body {"ready":true} |
| POST /ask không key | 401 | Codex gọi URL public, body {"detail":"Invalid or missing API key"} |
| POST /ask đúng key | 200 | Học viên tự chạy và gửi output ngày 25/11/2026 |

Response có key do học viên cung cấp:

```text
HTTP/2 200
content-type: application/json
date: Wed, 25 Nov 2026 09:25:02 GMT
server: railway-hikari
x-railway-request-id: LgQBbbAbQGye7VmAAax-fw
content-length: 168
x-hikari-trace: sin1.98a6
x-railway-edge: sin1

{"question":"What is deployment?","answer":"Deployment là quá trình đưa code từ máy bạn lên server để người khác dùng được.","cost_usd":2.01e-05}
```

## Screenshots — đã chụp thực tế

- [Dashboard](screenshots/dashboard.png): canvas Railway thấy agent và Redis Online.
- [Service running](screenshots/running.png): deployment Active và log startup của 2 worker.
- [API tests](screenshots/test.png): log request thực tế của /health 200, /ready 200, /ask 401 và /ask 200, không có secret.

Codex chụp trực tiếp giao diện Railway đã đăng nhập ngày 25/11/2026 theo yêu cầu học viên. test.png là ảnh log request trên Railway, không phải ảnh mô phỏng terminal; status khớp các lần gọi API đã ghi ở trên. Ảnh gốc JPEG được chuyển định dạng PNG để đúng tên file nộp bài, không sửa nội dung.

## Ghi chú cấu hình

CLI của học viên cảnh báo railway.toml deprecated và file hiện tại vẫn hoạt động tới 01/12/2026. Deploy này thành công ngày 25/11/2026 với file đó; nếu tiếp tục sử dụng sau mốc hỗ trợ cần kiểm tra hướng dẫn migration của Railway. Không đổi định dạng trong lần deploy đã kiểm chứng này.
