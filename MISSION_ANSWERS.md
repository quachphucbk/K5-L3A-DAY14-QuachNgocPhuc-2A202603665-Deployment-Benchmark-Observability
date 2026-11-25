# Day 14 Lab — Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns trong bản develop

Đối chiếu `01-localhost-vs-production/develop/app.py` với bản `production/`:

| # | Vị trí trong develop/app.py | Vấn đề | Tác động và hướng cải thiện |
|---|---|---|---|
| 1 | Dòng 17 | API key ghi trực tiếp trong source (key mẫu giả) | Key thật sẽ lộ khi chia sẻ repo; đọc từ biến môi trường hoặc secret manager. |
| 2 | Dòng 18 | URL database chứa tài khoản, mật khẩu hardcode | Lộ thông tin truy cập và khó đổi môi trường; dùng biến môi trường. |
| 3 | Dòng 21–22 | DEBUG và MAX_TOKENS là giá trị cố định | Muốn đổi cấu hình phải sửa code; tập trung cấu hình và đọc từ env. DEBUG khai báo ở đây không điều khiển reload bên dưới. |
| 4 | Dòng 33–38 | Dùng print cho log | Khó lọc theo mức độ và phân tích tự động; dùng logging với formatter JSON đúng chuẩn. |
| 5 | Dòng 34 | In API key ra log | Secret có thể lộ qua hệ thống thu thập log; không ghi giá trị secret vào log. |
| 6 | Toàn bộ route; chú thích dòng 42–43 | Không có /health và /ready | Hạ tầng không có endpoint chuyên biệt để kiểm tra sống/sẵn sàng; thêm liveness và readiness. |
| 7 | Dòng 51 | Bind vào localhost | Không nhận traffic từ ngoài container; dùng host cấu hình được, thường là 0.0.0.0 trong container. |
| 8 | Dòng 52 | Port 8000 cố định | Không dùng PORT do nền tảng inject; đọc PORT từ env. |
| 9 | Dòng 53 | reload=True cố định | File watcher phù hợp development, gây chi phí và restart ngoài ý muốn khi triển khai; chỉ bật ở chế độ debug. |
| 10 | Không có lifespan/cleanup của ứng dụng | Thiếu nơi quản lý startup và đóng tài nguyên khi shutdown | Thêm lifespan và phối hợp với cơ chế graceful shutdown của server. Uvicorn vẫn có shutdown mặc định; không thể kết luận develop luôn tắt đột ngột. |

### Exercise 1.2: Chạy basic version

Đã chạy HTTP server thật trên macOS, Python 3.12.16, FastAPI 0.115.0, Uvicorn 0.30.0, ngày 25/11/2026 (GMT+7). Dependencies cài trong môi trường ảo riêng; không cần API key LLM thật.

Để tránh chiếm cổng 8000 và tránh tiến trình reload, lần kiểm tra dùng CLI Uvicorn với cùng ứng dụng FastAPI, không sửa source:

```bash
# Từ 01-localhost-vs-production/develop/, trong môi trường đã cài requirements
python -m uvicorn app:app --host 127.0.0.1 --port 18001
```

Lệnh tái hiện request đã kiểm tra:

```bash
curl -i -X POST "http://127.0.0.1:18001/ask?question=What%20is%20Docker"
```

Kết quả HTTP thật (status và body; không chép các header biến động):

```text
HTTP 200
{
  "answer": "Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"
}
```

Kiểm tra bổ sung:

| Request | Mã HTTP đo được | Ý nghĩa |
|---|---:|---|
| GET / | 200 | App đang phục vụ |
| POST /ask?question=What%20is%20Docker | 200 | Gọi mock LLM thành công |
| POST /ask với JSON {} và không có query question | 422 | question là query parameter bắt buộc |
| GET /health | 404 | Chưa có liveness endpoint |
| GET /ready | 404 | Chưa có readiness endpoint |

Bản develop nhận question qua query, không nhận trường question từ JSON body. Chạy được một request chưa chứng minh ứng dụng đủ chuẩn production.

### Exercise 1.3: So sánh develop và production

Đã chạy bản production bằng chính entry point `python app.py`, với env thử nghiệm:

```bash
# Từ 01-localhost-vs-production/production/, trong môi trường đã cài requirements
HOST=127.0.0.1 PORT=18002 DEBUG=false ENVIRONMENT=staging python app.py
```

Host loopback chỉ dùng cho lần kiểm tra local. Mặc định trong config.py là 0.0.0.0, phù hợp container. Không đặt OPENAI_API_KEY: ứng dụng dùng mock LLM.

```bash
curl -i http://127.0.0.1:18002/health
curl -i http://127.0.0.1:18002/ready
curl -i -X POST http://127.0.0.1:18002/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is Docker"}'
```

| Feature | Develop | Production | Tại sao quan trọng? |
|---|---|---|---|
| Config | Hằng số trong app.py | Settings đọc env ở config.py:17–34 | Cùng code chạy được ở dev/staging/production bằng cấu hình khác nhau. |
| Secret | Hardcode và in key ra log | Đọc OPENAI_API_KEY/AGENT_API_KEY từ env; request log chỉ ghi metadata | Giảm nguy cơ lộ key và dễ thay key. Cấu hình AGENT_API_KEY chưa đồng nghĩa endpoint đã có xác thực. |
| Host/port | localhost:8000 cố định | HOST, PORT từ env; app.py:194–198 | Nhận được traffic container và dùng port của nền tảng. Đã xác minh PORT=18002 có hiệu lực. |
| Debug/reload | reload luôn bật | reload theo settings.debug | Tách chế độ phát triển với triển khai. |
| Health check | /health trả 404 | /health trả 200, có uptime/version/environment; app.py:135–149 | Cho phép hạ tầng kiểm tra process đang phục vụ. |
| Readiness | /ready trả 404 | /ready trả 200 khi is_ready=True; app.py:152–161 | Phân biệt còn sống với sẵn sàng nhận traffic. Bản mẫu chỉ kiểm tra cờ, chưa ping Redis/database. |
| Logging | print, có in key | Có ý định dùng logging và JSON; app.py:28–31, 111–122 | Log có cấu trúc giúp tìm và tổng hợp sự kiện; bản mẫu vẫn có lỗi cấu hình, ghi rõ bên dưới. |
| Lifecycle/shutdown | Không có cleanup riêng | Lifespan startup/shutdown, đổi is_ready; app.py:39–67 | Có nơi khởi tạo và đóng tài nguyên. Cần để Uvicorn xử lý request đang chạy trước khi thoát. |
| Input | question qua query | Đọc question từ JSON body; thiếu/rỗng trả 422 | Giao diện API khác nhau, phải gửi request đúng dạng. |

Kết quả API production đo được:

```json
{
  "root": {
    "status": 200,
    "body": {
      "app": "AI Agent",
      "version": "1.0.0",
      "environment": "staging",
      "status": "running"
    }
  },
  "ask": {
    "status": 200,
    "body": {
      "question": "What is Docker",
      "answer": "Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!",
      "model": "gpt-4o-mini"
    }
  },
  "health": {
    "status": 200,
    "body": {
      "status": "ok",
      "uptime_seconds": 0.3,
      "version": "1.0.0",
      "environment": "staging",
      "timestamp": "2026-11-25T08:01:00.625064+00:00"
    }
  },
  "ready": {
    "status": 200,
    "body": {
      "ready": true
    }
  },
  "missing_question": {
    "status": 422,
    "body": {
      "detail": "question field is required"
    }
  }
}
```

#### Nhận xét từ kiểm tra thực tế

- Khi gửi SIGTERM lúc server rảnh, cả hai server đều kết thúc trong thời hạn kiểm tra 5 giây và có log `Application shutdown complete.`. Production thoát với code 0; develop chạy qua CLI Uvicorn có return code -15. Chưa thử SIGTERM trong lúc request đang xử lý, nên chưa khẳng định đã chứng minh hoàn tất in-flight request.
- Logging của production chưa đạt mục tiêu mỗi dòng app log là JSON: `config.py` gọi `logging.warning` trước `logging.basicConfig`, khiến root handler mặc định đã được tạo. Lần chạy xuất dòng `WARNING:root:OPENAI_API_KEY not set — using mock LLM`; log INFO của app bị lọc. Ngoài ra formatter chèn `%(message)s` vào chuỗi JSON không escape dấu nháy, có thể tạo JSON không hợp lệ với message đã json.dumps. Hướng cải thiện: cấu hình logging trước khi validate config, dùng formatter trả json.dumps cho toàn bộ record. Chưa sửa code mẫu trong Part 1.
- `config.py` dùng os.getenv, chưa thấy load_dotenv hay cơ chế tự đọc .env. Vì vậy lần kiểm tra truyền env trực tiếp; chỉ copy .env.example thành .env chưa đảm bảo biến được nạp khi chạy python app.py.
- Trường model trả về là tên cấu hình; request thực tế gọi utils.mock_llm.ask, không gọi dịch vụ LLM bên ngoài.

### Giải thích các nguyên tắc chính

1. **Config trong environment:** giữ code giống nhau, thay biến theo môi trường; không đặt secret vào source.
2. **Dependencies khai báo rõ:** requirements.txt ghi các dependency trực tiếp và phiên bản, giúp dựng môi trường nhất quán hơn.
3. **Stateless process:** state dùng chung nên nằm ở Redis/database, vì các worker/instance có bộ nhớ riêng.
4. **Disposability:** startup nhanh, khi nhận tín hiệu tắt phải hoàn tất công việc đang chạy và đóng tài nguyên.
5. **Dev/prod parity:** giảm khác biệt runtime, dependencies và backing services để lỗi được phát hiện sớm.

### Câu hỏi thảo luận

- **Push key thật lên GitHub public:** người khác có thể lấy và sử dụng key; cần thu hồi/đổi key, kiểm tra sử dụng và xử lý lịch sử git. Xóa dòng hiện tại không xóa secret trong commit cũ.
- **Stateless quan trọng khi scale:** request kế tiếp có thể tới instance khác; state trong RAM của instance trước sẽ không truy cập được. Lưu state bên ngoài giúp các instance chia sẻ dữ liệu.
- **Health khác readiness:** health kiểm tra process còn phục vụ; readiness kiểm tra đã sẵn sàng nhận nghiệp vụ. Ví dụ Redis mất kết nối thì process vẫn có thể sống nhưng chưa sẵn sàng xử lý nghiệp vụ phụ thuộc Redis.

### Xác nhận học viên đã chạy lại Part 1

Ngày 25/11/2026, học viên xác nhận đã tự chạy xong Part 1 theo hướng dẫn và kết quả đúng kỳ vọng:

| Kiểm tra | Kết quả học viên xác nhận |
|---|---|
| Develop: GET / và POST /ask với question qua query | 200, nhận được câu trả lời mock |
| Develop: GET /health và GET /ready | 404 |
| Production: GET /, GET /health và GET /ready | 200; environment là staging, ready là true |
| Production: POST /ask với JSON có question | 200, có question/answer/model |
| Production: POST /ask với JSON {} | 422, question field is required |
| Production: đổi PORT sang 8003 và gọi /health | 200 |

Nguồn xác nhận: học viên báo đã chạy xong và đúng kỳ vọng trong chat. Các JSON và kết quả SIGTERM ở trên vẫn là bằng chứng từ lần Codex chạy thực tế trước đó; chưa có bản chép terminal mới hoặc ảnh do học viên gửi để đính kèm.

## Part 2: Docker

### Exercise 2.1: Dockerfile cơ bản

1. **Base image:** `python:3.11` (bản full), theo lệnh FROM trong `02-docker/develop/Dockerfile`. Không phải `python:3.11-slim` như một đáp án minh họa trong tài liệu.
2. **Working directory:** `/app`; các lệnh RUN, COPY với đích tương đối và CMD hoạt động từ thư mục này.
3. **COPY requirements trước source:** Docker tái sử dụng layer cài dependencies khi requirements không đổi, dù source thay đổi. Nếu copy toàn bộ source trước bước pip install, sửa source sẽ làm mất cache của bước cài dependencies phía sau.
4. **CMD và ENTRYPOINT:** CMD đặt lệnh/tham số mặc định, có thể thay bằng các đối số sau tên image khi docker run. ENTRYPOINT đặt chương trình chính; với exec form, đối số docker run thường được nối vào chương trình đó. Có thể ghi đè ENTRYPOINT bằng --entrypoint. Dockerfile develop dùng `CMD ["python", "app.py"]`.

### Exercise 2.2: Build và chạy bản develop

Build từ gốc repo vì các đường dẫn COPY được tính theo build context:

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run --rm --name day14-basic -p 8000:8000 my-agent:develop
```

Image develop đã build thành công, ID `b494e1eb4c26`, được xác nhận bằng output docker images học viên gửi ở Exercise 2.3. Học viên đã chạy container develop và cung cấp output hai request dưới đây; cả hai trả HTTP 200.

Lệnh kiểm tra develop do học viên thực hiện:

```bash
curl -i http://localhost:8000/health
curl -i -X POST "http://localhost:8000/ask?question=What%20is%20Docker"
```

Kết quả thực tế do học viên gửi ngày 25/11/2026:

**GET /health:**

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 08:56:49 GMT
server: uvicorn
content-length: 54
content-type: application/json

{"status":"ok","uptime_seconds":26.2,"container":true}
```

**POST /ask?question=What%20is%20Docker:**

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 08:56:59 GMT
server: uvicorn
content-length: 103
content-type: application/json

{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

Kết luận: container develop phục vụ được health check và trả lời qua mock LLM; body health có container=true. Bằng chứng này thuộc bản Docker develop của Part 2, khác bản localhost develop Part 1 vốn chưa có /health.

### Exercise 2.3: Multi-stage và so sánh kích thước image

- **Builder:** dùng python:3.11-slim, cài gcc/libpq-dev và dependencies Python vào /root/.local.
- **Runtime:** bắt đầu từ python:3.11-slim mới, copy packages từ builder và source cần chạy, dùng appuser non-root, có HEALTHCHECK và chạy Uvicorn 2 worker.
- **Lý do nhỏ hơn:** thay base full bằng slim và không mang layer cài gcc/libpq-dev của builder vào runtime. Việc giảm kích thước ở đây đến từ cả slim base và multi-stage, không chỉ từ multi-stage.

Output học viên gửi ngày 25/11/2026:

```text
IMAGE               ID             DISK USAGE   CONTENT SIZE
my-agent:advanced   338ad7ee1823        265MB         57.5MB
my-agent:develop    b494e1eb4c26       1.67GB          415MB
```

| Chỉ số | Develop | Advanced | Mức giảm xấp xỉ |
|---|---:|---:|---:|
| DISK USAGE | 1.67 GB (≈ 1670 MB) | 265 MB | 84.13% |
| CONTENT SIZE | 415 MB | 57.5 MB | 86.14% |

Tính trên cùng cột, không trộn DISK USAGE với CONTENT SIZE:

- DISK USAGE: (1670 − 265) / 1670 × 100 ≈ 84.13%.
- CONTENT SIZE: (415 − 57.5) / 415 × 100 ≈ 86.14%.
- Giá trị là xấp xỉ vì output Docker đã làm tròn. Image advanced có DISK USAGE 265 MB, dưới 500 MB.

Trong quá trình build gặp Docker Hub HTTP 429 ở bước tải metadata python:3.11-slim. Đây là lỗi giới hạn request phía registry; sau đó học viên đã build thành công. Không ghi nhận thêm cách khắc phục cụ thể chưa được học viên xác nhận.

### Exercise 2.4: Docker Compose stack

Cấu hình trong `02-docker/production/docker-compose.yml` có agent, redis, qdrant, nginx. Sơ đồ theo cấu hình:

```text
Client → localhost:80 → Nginx → Agent:8000
                                 ├→ Redis:6379
                                 └→ Qdrant:6333
```

Các service cùng Docker network internal, giao tiếp qua tên service. Agent được cấu hình REDIS_URL và QDRANT_URL; Nginx proxy request vào agent. Đây là sơ đồ kết nối cấu hình, không khẳng định mỗi request /ask đều truy cập Redis và Qdrant.

Lệnh chạy theo hướng dẫn (từ 02-docker/production):

```bash
touch .env.local
docker compose -p k5-day14-docker up -d --build
docker compose -p k5-day14-docker ps
```

**Bằng chứng do học viên chạy và gửi trong chat:**

```bash
curl -i http://localhost/health
```

```text
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 25 Nov 2026 08:50:23 GMT
Content-Type: application/json
Content-Length: 96
Connection: keep-alive
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block

{"status":"ok","uptime_seconds":64.3,"version":"2.0.0","timestamp":"2026-11-25T08:50:23.129514"}
```

```bash
curl -i -X POST http://localhost/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Explain microservices"}'
```

```text
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 25 Nov 2026 08:50:28 GMT
Content-Type: application/json
Content-Length: 126
Connection: keep-alive
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

Hai request đi qua Nginx đều trả 200, chứng minh health endpoint và luồng proxy tới agent hoạt động tại thời điểm kiểm tra. Mock trả câu trả lời mẫu; HTTP 200 không chứng minh chất lượng trả lời về microservices. Output docker compose ps do học viên bổ sung xác nhận Agent, Redis và Qdrant healthy; Nginx đang chạy và publish cổng 80/443.



**Bằng chứng trạng thái Compose do học viên cung cấp:**

```bash
docker compose -p k5-day14-docker ps
```

| Container | Service | Trạng thái | Cổng |
|---|---|---|---|
| k5-day14-docker-agent-1 | agent | Up 39 seconds (healthy) | 8000/tcp nội bộ |
| k5-day14-docker-nginx-1 | nginx | Up 39 seconds | Host 80 → 80, 443 → 443 |
| k5-day14-docker-qdrant-1 | qdrant | Up 50 seconds (healthy) | 6333–6334/tcp nội bộ |
| k5-day14-docker-redis-1 | redis | Up 50 seconds (healthy) | 6379/tcp nội bộ |

Trạng thái healthy là kết quả healthcheck tại thời điểm chụp output, không thay thế kiểm tra nghiệp vụ. Publish cổng 443 không tự chứng minh HTTPS đã có chứng chỉ và hoạt động.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

Đã deploy agent Part 6 lên Railway, URL https://agent-production-b103e56c.up.railway.app. Project day14-agent, service agent, environment production; service Redis Online với volume. Lệnh deploy từ 06-lab-complete: railway up . --path-as-root --service agent. Secret đặt qua env, không ghi key vào bài.

Kiểm tra URL public: /health 200, /ready 200, POST /ask không key 401 (Codex thực hiện); POST /ask đúng key 200 (học viên thực hiện, output timestamp 25/11/2026 09:25:02 GMT). Chi tiết lệnh và response trong DEPLOYMENT.md. Đã có 3 ảnh thật do Codex chụp trên Railway theo yêu cầu học viên: screenshots/dashboard.png, running.png, test.png (log 4 request API).

### Exercise 3.2: So sánh Railway và Render

Chọn Railway làm nền tảng chính; không cần deploy thêm Render để lấy điểm so sánh.

| Nội dung | Railway | Render |
|---|---|---|
| File cấu hình trong bài | railway.toml, cú pháp TOML | render.yaml, cú pháp YAML, khai báo danh sách services |
| Build agent Part 6 | DOCKERFILE dùng Dockerfile multi-stage đã kiểm tra | Mẫu 03-cloud-deployment/render dùng runtime Python, pip install và startCommand; nếu deploy Part 6 phải chỉnh path/runtime cho đúng |
| Start/port | CMD Dockerfile dùng PORT; mẫu Railway Part 3 cũ dùng NIXPACKS/startCommand | Mẫu có buildCommand/startCommand và $PORT |
| Health | healthcheckPath = "/health" | healthCheckPath: /health |
| Secrets | Đặt qua dashboard/CLI, reference biến service khác | envVars, sync:false hoặc generateValue:true; không ghi giá trị key thật |
| Redis | Lần triển khai này tạo service riêng, agent tham chiếu Redis.REDIS_URL | Mẫu YAML khai báo thêm service Redis nhưng cần nối REDIS_URL của web service tới Redis |

Khác biệt do mô hình cấu hình của từng nền tảng; không thể đổi tên TOML thành YAML và dùng nguyên nội dung. Nhận xét trên đối chiếu file mẫu trong repo, không khẳng định plan/tính năng ghi trong mẫu vẫn là chính sách hiện hành. CLI đã cảnh báo Config as Code deprecated, còn hoạt động tới 01/12/2026; deployment này dùng thành công ngày 25/11/2026.

### Exercise 3.3: Mô tả pipeline Cloud Run

1. cloudbuild.yaml khai báo bước cài requirements/pytest rồi chạy tests/; build được cấu hình chờ bước test.
2. Build Docker image gắn tag COMMIT_SHA và latest, rồi push các tag lên registry gcr.io/$PROJECT_ID/ai-agent theo file mẫu.
3. Bước deploy dùng gcloud run deploy tại asia-southeast1, image theo COMMIT_SHA, 1 CPU/512 MiB, min 1/max 10 instance, timeout 60 giây và tham chiếu secret.
4. service.yaml mô tả service, concurrency 80, tài nguyên, env/secret, liveness /health và startup /ready; là cách khai báo service riêng, không được cloudbuild.yaml áp dụng tự động.
5. Chỉ đọc cấu hình theo yêu cầu K5, chưa chạy GCP. Chú ý bước test mẫu không bật set -e và có echo cuối nên cần sửa nếu muốn bảo đảm pytest fail thực sự chặn pipeline; trigger push main cũng phải cấu hình ở Cloud Build, không tự sinh từ chú thích YAML.

## Part 4: API Security

### Exercise 4.1: API Key authentication

Code `04-api-gateway/develop/app.py` đọc AGENT_API_KEY từ môi trường. Dependency verify_api_key lấy header X-API-Key với auto_error=False, tự xử lý thiếu key; endpoint /ask dùng Depends(verify_api_key).

Kết quả học viên tự chạy và gửi ngày 25/11/2026:

| Trường hợp | HTTP thực tế | Nội dung |
|---|---|---|
| Không có X-API-Key | 401 Unauthorized | Missing API key. Include header: X-API-Key: <your-key> |
| Key sai (wrong-key) | 403 Forbidden | Invalid API key. |
| Key đúng (key thử nghiệm được đặt qua AGENT_API_KEY) | 200 OK | Có question và answer |

```text
# Không có key — 08:59:05 GMT
HTTP/1.1 401 Unauthorized
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

# Key sai — 08:59:16 GMT
HTTP/1.1 403 Forbidden
{"detail":"Invalid API key."}

# Key đúng — 08:59:25 GMT
HTTP/1.1 200 OK
{"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

- Key được kiểm tra trước khi thực thi business logic của /ask. Thiếu key hoặc key sai đều bị chặn.
- Mã 403 khi key sai đúng với code mẫu Part 4; hướng dẫn AI trước đó dự đoán 401 là sai. Không sửa output thực tế cho khớp dự đoán.
- Part 6 có hợp đồng riêng: cả thiếu và sai key phải trả 401.
- Rotate key: thay AGENT_API_KEY trong môi trường triển khai và restart/redeploy để process đọc key mới; cập nhật client, thu hồi key cũ. Không commit key thật và không in key ra log. Bản mẫu hiện còn print key khi startup, cần tránh khi triển khai thật.

### Exercise 4.2: JWT authentication

Học viên lấy token qua POST /auth/token với tài khoản mẫu student, rồi gọi POST /ask bằng header Authorization: Bearer $TOKEN. Không lưu token vào bài.

```bash
curl -i -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Explain JWT"}'
```

Output học viên cung cấp:

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 09:01:20 GMT
server: uvicorn
content-length: 184
content-type: application/json
vary: Origin
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin

{"question":"Explain JWT","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":9,"budget_remaining_usd":1.6e-05}}
```

Kết luận: token được API chấp nhận và request thành công. Đây là kiểm tra xác thực, không phải kiểm tra độ đúng của câu trả lời về JWT, vì agent dùng mock LLM. Các trường usage được ghi nguyên theo response; chưa kết luận budget_remaining_usd là số dư thật trước khi đọc cost_guard.py.

### Exercise 4.3: Rate limiting

Bằng chứng học viên cung cấp: vòng lặp 20 request dùng cùng JWT trả 200 ở request 01–09, 429 ở request 10–20. Request JWT thành công ở Exercise 4.2 cũng nằm trong cùng cửa sổ, nên tổng request được chấp nhận là 10.

```text
Request 01: 200
Request 02: 200
Request 03: 200
Request 04: 200
Request 05: 200
Request 06: 200
Request 07: 200
Request 08: 200
Request 09: 200
Request 10: 429
Request 11: 429
Request 12: 429
Request 13: 429
Request 14: 429
Request 15: 429
Request 16: 429
Request 17: 429
Request 18: 429
Request 19: 429
Request 20: 429
```

Request kiểm tra ngay sau vòng lặp:

```text
HTTP/1.1 429 Too Many Requests
date: Wed, 25 Nov 2026 09:02:01 GMT
server: uvicorn
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
x-ratelimit-reset: 1795597381
retry-after: 20
content-length: 98
content-type: application/json
vary: Origin
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":20}}
```

Đối chiếu rate_limiter.py và app.py:

- Mỗi user có deque chứa timestamp. Khi request tới, bỏ timestamp cũ ngoài 60 giây, đếm phần còn lại rồi chặn hoặc thêm timestamp mới. Đây là sliding window theo log timestamp, dù docstring gọi là Sliding Window Counter; không phải token bucket.
- User thường được 10 request/60 giây; admin được 100 request/60 giây. app.py chọn limiter dựa vào role đã xác minh từ JWT; admin không được bypass vô hạn.
- Retry-After: 20 yêu cầu client chờ khoảng 20 giây trước khi thử lại. Header X-RateLimit-Reset của mẫu được tính now + window, không nên coi đó là thời điểm chính xác lượt đầu tiên hết hạn; Retry-After được tính từ timestamp cũ nhất.
- State nằm trong RAM, mất khi restart và không chia sẻ giữa worker/instance. Part 6 cần chuyển state sang Redis.

### Exercise 4.4: Cost guard — đối chiếu code mẫu

- CostGuard của Part 4 lưu state trong RAM, giới hạn 1 USD/ngày/user và 10 USD/ngày toàn hệ thống; chưa phải yêu cầu Redis 10 USD/tháng của Exercise 4.4.
- Luồng /ask: xác minh JWT → rate limit → check_budget → gọi mock LLM → record_usage. Rate limit bảo vệ số request; cost guard bảo vệ tiền vì mỗi request có thể có lượng token và chi phí khác nhau.
- Công thức trong code mẫu: cost = input_tokens/1000 × PRICE_PER_1K_INPUT_TOKENS + output_tokens/1000 × PRICE_PER_1K_OUTPUT_TOKENS. Đây là hằng số minh họa của bài, không phải xác nhận giá model hiện hành.
- Vượt ngân sách user: 402; vượt ngân sách toàn cục: 503. Usage user được tạo lại khi đổi ngày. _global_today chưa được dùng để reset _global_cost, nên bộ đếm toàn cục chưa tự reset theo ngày đúng mục tiêu.
- app.py gán trường usage.budget_remaining_usd trong response /ask bằng usage.total_cost_usd. Vì vậy 1.6e-05 trong bằng chứng JWT là chi phí đã dùng bị gắn nhãn sai, không phải số dư. Endpoint GET /me/usage gọi get_usage, tính số dư bằng budget − cost.

#### Bằng chứng GET /me/usage

Học viên tự chạy và cung cấp:

```bash
curl -i http://localhost:8000/me/usage \
  -H "Authorization: Bearer $TOKEN"
```

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 09:03:56 GMT
server: uvicorn
content-length: 184
content-type: application/json
vary: Origin
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin

{"user_id":"student","date":"2026-11-25","requests":10,"input_tokens":58,"output_tokens":296,"cost_usd":0.000186,"budget_usd":1.0,"budget_remaining_usd":0.999814,"budget_used_pct":0.0}
```

Đối chiếu: 58/1000 × 0.00015 + 296/1000 × 0.0006 = 0.0001863 USD; code làm tròn thành 0.000186 USD. Số dư 1 − 0.000186 = 0.999814 USD. budget_used_pct=0.0 là do làm tròn một chữ số thập phân, không phải chưa tiêu token. requests=10 khớp 1 request JWT và 9 request được chấp nhận ở vòng lặp; request bị rate limit không gọi LLM và không ghi usage.

#### Thiết kế cost guard Redis 10 USD/tháng theo Exercise 4.4

Đây là đề xuất triển khai theo yêu cầu bài, chưa thay thế code mẫu Part 4 và chưa được chạy kiểm tra Redis/402:

1. Dùng user_id lấy từ danh tính đã xác thực, không tin user_id tùy ý từ body. Tạo key `budget:<user_id>:<YYYY-MM>` theo UTC, ngân sách 10 USD cho mỗi user mỗi tháng. Đọc budget từ cấu hình.
2. Ước tính chi phí trước khi gọi LLM dựa trên input token và giới hạn output token. Quy đổi tiền sang đơn vị nguyên đủ nhỏ để tránh sai số float (ví dụ nano-USD).
3. Thực hiện kiểm tra và giữ chỗ chi phí bằng một Redis Lua script nguyên tử: đọc tổng đã dùng/đã giữ chỗ; nếu tổng + ước tính > giới hạn thì từ chối (API trả 402); nếu còn budget thì INCRBY số ước tính. Gắn EXPIREAT vào đầu tháng kế tiếp theo UTC. Không tách GET/check/INCR thành các request độc lập vì nhiều instance có thể đồng thời vượt ngân sách.
4. Sau khi LLM hoàn thành, đối soát chi phí thực tế và phần giữ chỗ trong Redis. Dùng request_id để tránh ghi nhận hai lần khi retry; nếu upstream lỗi vẫn phải tính phần chi phí thực tế nhà cung cấp đã phát sinh. Giới hạn token để chi phí thực tế không vượt phần đã giữ chỗ.
5. Sang tháng mới dùng key YYYY-MM mới nên tổng bắt đầu từ 0; TTL dọn key cũ. State nằm trong Redis dùng chung nên vẫn có hiệu lực khi restart agent hoặc scale nhiều instance. Redis dùng volume/persistence nếu cần giữ state khi Redis restart.
6. Khi Redis không truy cập được, trả 503 để không gọi LLM ngoài kiểm soát. Khi vượt ngân sách trả 402 và thông báo kỳ reset; không lộ secret hay stack trace.

Khác biệt với rate limit: cùng 10 request có thể có chi phí rất khác nhau theo token/model, nên phải kiểm soát cả tốc độ và tiền. Kiểm tra cần có cho bản Redis: còn budget được phép gọi; vượt budget bị 402; đổi tháng reset; restart agent không mất số đã dùng; request đồng thời không vượt hạn mức. Các kiểm tra Redis này chưa được ghi nhận là đã chạy trong Part 4.



## Part 5: Scaling & Reliability

### Exercise 5.1: Liveness và readiness

Output học viên tự chạy và cung cấp ngày 25/11/2026:

```bash
curl -i http://localhost:8000/health
```

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 09:06:43 GMT
server: uvicorn
content-length: 185
content-type: application/json

{"status":"ok","uptime_seconds":8.3,"version":"1.0.0","environment":"development","timestamp":"2026-11-25T09:06:45.147667+00:00","checks":{"memory":{"status":"ok","used_percent":80.4}}}
```

```bash
curl -i http://localhost:8000/ready
```

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 09:07:30 GMT
server: uvicorn
content-length: 37
content-type: application/json

{"ready":true,"in_flight_requests":1}
```

- Liveness: process có phục vụ được không; /health trả 200, báo uptime và bộ nhớ hệ thống theo psutil.virtual_memory(). used_percent=80.4 không phải riêng RAM của process agent.
- Readiness: instance sẵn sàng nhận traffic nghiệp vụ chưa; /ready trả 200 với ready=true. Bản develop kiểm tra cờ _is_ready, chưa chứng minh kiểm tra Redis/database.
- in_flight_requests=1 bao gồm chính request /ready vì middleware tăng counter trước khi gọi endpoint; không chứng minh đang có một request nghiệp vụ khác.
- Nếu readiness không đạt thì ngừng route traffic tới instance; liveness lỗi kéo dài có thể khiến hạ tầng restart process/container tùy cấu hình probe.

### Exercise 5.2: Graceful shutdown

Học viên gửi request mock (delay khoảng 3 giây), đợi 0.5 giây rồi gửi SIGTERM tới PID server 59882:

```bash
AGENT_PID=59882
curl -i -X POST "http://localhost:8000/ask?question=hello" &
REQUEST_PID=$!
sleep 0.5
kill -TERM "$AGENT_PID"
wait "$REQUEST_PID"
```

Kết quả request do học viên cung cấp:

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 09:09:09 GMT
server: uvicorn
content-length: 126
content-type: application/json

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

Log phía server do học viên cung cấp:

```text
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:49682 - "GET /ready HTTP/1.1" 200 OK
INFO:     Shutting down
INFO:     127.0.0.1:49757 - "POST /ask?question=hello HTTP/1.1" 200 OK
INFO:     Waiting for application shutdown.
2026-11-25 16:09:12,520 INFO 🔄 Graceful shutdown initiated...
2026-11-25 16:09:12,520 INFO ✅ Shutdown complete
INFO:     Application shutdown complete.
INFO:     Finished server process [59882]
2026-11-25 16:09:12,521 INFO Received signal 15 — uvicorn will handle graceful shutdown
```

Kết luận: trong lần thử này, server bắt đầu shutdown, request đang xử lý vẫn trả 200, sau đó application shutdown complete và process kết thúc. Uvicorn điều phối dừng nhận kết nối và chờ request; lifespan chạy cleanup. SIGTERM cho phép tắt có kiểm soát, khác SIGKILL không cho ứng dụng cleanup. Chưa thu exit code bằng wait cho process server; không suy diễn exit code 0 chỉ từ log.

Giới hạn: ask() dùng time.sleep trong async endpoint nên chặn event loop; lần thử chứng minh request sống sót và process tắt, chưa chứng minh mọi hành vi shutdown dưới tải đồng thời. Trong bản production thật nên tránh I/O blocking trên event loop.

### Exercise 5.3: Stateless design

State hội thoại nằm trong Redis dùng chung thay vì dict trong RAM của từng agent. Client gửi cùng session_id; bất kỳ instance nào nhận request cũng có thể đọc/ghi history của session đó. Stateless ở đây nghĩa là agent không giữ state hội thoại riêng cần thiết cho request tiếp theo; hệ thống vẫn có state trong Redis.

```text
Client → Nginx (host :8080 → container :80)
            ├→ Agent 1:8000 ─┐
            ├→ Agent 2:8000 ─┼→ Redis:6379
            └→ Agent 3:8000 ─┘
```

### Exercise 5.4: Load balancing

Học viên chạy trong 05-scaling-reliability/production:

```bash
touch .env.local
docker compose -p k5-day14-scaling up -d --build --scale agent=3
docker compose -p k5-day14-scaling ps
```

Kết quả ps học viên cung cấp:

| Container | Service | Trạng thái | Cổng |
|---|---|---|---|
| k5-day14-scaling-agent-1 | agent | Up 5 seconds (healthy) | 8000/tcp nội bộ |
| k5-day14-scaling-agent-2 | agent | Up 5 seconds (healthy) | 8000/tcp nội bộ |
| k5-day14-scaling-agent-3 | agent | Up 5 seconds (healthy) | 8000/tcp nội bộ |
| k5-day14-scaling-nginx-1 | nginx | Up 5 seconds | Host 8080 → 80 |
| k5-day14-scaling-redis-1 | redis | Up 16 seconds (healthy) | 6379/tcp nội bộ |

Nginx là đầu vào duy nhất tại localhost:8080 và phân phối request tới agent. Test dưới đây quan sát được cả 3 instance nhận request.

### Exercise 5.5: Test stateless

```bash
python3 test_stateless.py
```

Output chính do học viên cung cấp:

```text
Stateless Scaling Demo
Session ID: c591569c-6ba8-4109-a4de-e8b518ed2f5c

Request 1: [instance-52c1d1]
  Q: What is Docker?
Request 2: [instance-7fd686]
  Q: Why do we need containers?
Request 3: [instance-fef628]
  Q: What is Kubernetes?
Request 4: [instance-52c1d1]
  Q: How does load balancing work?
Request 5: [instance-7fd686]
  Q: What is Redis used for?

Total requests: 5
Instances used: {'instance-7fd686', 'instance-fef628', 'instance-52c1d1'}
✅ All requests served despite different instances!

--- Conversation History ---
Total messages: 10
  [user]: What is Docker?...
  [assistant]: Container là cách đóng gói app để chạy ở mọi nơi. Build once...
  [user]: Why do we need containers?...
  [assistant]: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã đư...
  [user]: What is Kubernetes?...
  [assistant]: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã đư...
  [user]: How does load balancing work?...
  [assistant]: Đây là câu trả lời từ AI agent (mock). Trong production, đây...
  [user]: What is Redis used for?...
  [assistant]: Đây là câu trả lời từ AI agent (mock). Trong production, đây...

✅ Session history preserved across all instances via Redis!
```

Kết luận: 5 request trong cùng session được phục vụ bởi 3 instance; history giữ đủ 5 cặp user/assistant, tổng 10 tin nhắn. Kết quả xác nhận luồng chia sẻ history giữa các instance hoạt động trong lần thử. Script không tự kill/restart agent hoặc Redis; chưa kết luận đã kiểm tra failover hay độ bền dữ liệu sau Redis restart.



## Part 6: Final Project

### Thực hiện và kiểm tra

Codex đã sửa 11 file TODO trong 06-lab-complete, giữ nguyên check_production_ready.py và utils/mock_llm.py:

- Config đọc env, hỗ trợ .env local; API key thiếu hoặc sai trả 401.
- /health không phụ thuộc Redis; /ready kiểm tra Redis, lỗi trả 503.
- Rate limit sliding window nguyên tử bằng Redis Lua, chia sẻ state giữa worker và giữ state sau restart agent. Key API được hash trước khi dùng trong tên key Redis.
- Cost guard theo DAILY_BUDGET_USD: giữ chỗ chi phí ước tính nguyên tử trước khi gọi mock, đối soát chi phí sau đó; dùng số nguyên nano-USD và key theo ngày UTC. Giới hạn output ước tính lấy từ tập câu trả lời mock có sẵn; không coi đó là cách ước tính đủ cho LLM thật.
- Log app dùng formatter json.dumps; lifespan đóng Redis, Uvicorn điều phối graceful shutdown. Endpoint nghiệp vụ đồng bộ để mock blocking chạy trong threadpool.
- Docker multi-stage slim, non-root, HEALTHCHECK, PORT từ env; Compose có agent + Redis với volume AOF.
- railway.toml dùng DOCKERFILE và healthcheckPath=/health. Đã deploy Railway ở Part 3; URL và kiểm tra thực tế trong DEPLOYMENT.md.

Lệnh Codex đã chạy trong 06-lab-complete trên máy có Docker:

```bash
.venv/bin/python check_production_ready.py
```

Kết quả thực tế bản đầy đủ ngày 25/11/2026: **PASS 12/12; 41/41 checks passed**. Image 297 MB; build 11 giây; docker stop exit code 0 trong 0.4 giây. Script xác nhận rate limit sau restart, readiness khi Redis down, 402 với ngân sách nhỏ, 12 dòng app log JSON hợp lệ, request đang chạy vẫn 200 khi SIGTERM và process thoát code 0.

```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 41/41 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
================================================================

```

Output đầy đủ lưu tại reports/part6-production-ready.txt. Output trong reports/part6-production-ready.txt là lần chạy do Codex thực hiện. Học viên sau đó tự chạy lại bản đầy đủ và cung cấp output xác nhận PASS 12/12, 41/41 checks; lần chạy của học viên build mất 1 giây, image 297 MB, docker stop exit code 0 trong 0.4 giây. PASS mục Public URL ready kiểm tra cấu hình triển khai, không chứng minh có URL public; Part 3 vẫn phải deploy và kiểm tra URL thật.

Giới hạn của cost guard: nếu process chết sau khi giữ chỗ mà chưa đối soát, phần giữ chỗ có thể còn tính vào budget tới hết ngày. Với dịch vụ thật cần đối soát có request_id, số token/billing thực tế và kiểm thử thêm các trường hợp lỗi đồng thời.

### Xác nhận học viên chạy lại Part 6

Ngày 25/11/2026, học viên chạy `python check_production_ready.py` trong `06-lab-complete/`, không dùng --static-only hoặc --skip-docker, rồi cung cấp toàn bộ output trong chat:

```text
Docker: build image thành công — 1s
Docker: image < 500 MB — 297 MB
Khi chạy: SIGTERM lúc đang có request → request vẫn 200, process tự thoát — exit code 0
Docker: docker stop tắt êm (exit code 0, < 10s) — exit code 0, 0.4s
Result: 12/12 tiêu chí đạt · 41/41 checks passed
🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

Đây là kết quả chạy local do học viên cung cấp. URL cloud đã được triển khai và kiểm tra trong Part 3; xem DEPLOYMENT.md.

## Part 7: Benchmark & Observability — ghi chú thực hành

### Exercise 7.1: Metrics

Output học viên cung cấp từ POST http://localhost:8002/ask ngày 25/11/2026, 09:29:33 GMT:

```text
HTTP/1.1 200 OK
x-request-id: c07b86f245e8
{"answer":"Prometheus pull metrics bằng cách scrape endpoint /metrics theo chu kỳ. Counter chỉ tăng (đếm request), Gauge lên xuống (request đang xử lý), Histogram chia latency vào các bucket để tính percentile bằng histogram_quantile.","model":"mock-llm-small","agent_version":"v2","usage":{"input_tokens":91,"output_tokens":55,"cost_usd":4.665e-05},"llm_latency_ms":142.3,"request_id":"c07b86f245e8"}
```

Các metric học viên quan sát:

| Loại | Metric | Giá trị quan sát | Ý nghĩa |
|---|---|---|---|
| Counter | http_requests_total{method="POST",route="/ask",status="200"} | 1 | Một request /ask thành công |
| Gauge | agent_in_flight_requests | 0 | Không có request được đếm đang xử lý khi scrape |
| Histogram | http_request_duration_seconds_bucket{le="0.1",method="POST",route="/ask"} | 0 | Không request nào mất tối đa 0.1 giây |
| Histogram | http_request_duration_seconds_bucket{le="0.2",method="POST",route="/ask"} | 1 | Một request mất tối đa 0.2 giây |
| Counter | llm_tokens_total{model="mock-llm-small",type="input"} | 91 | Token input |
| Counter | llm_tokens_total{model="mock-llm-small",type="output"} | 55 | Token output |
| Counter | llm_cost_usd_total{model="mock-llm-small"} | 4.6649999999999996e-05 | Chi phí mô phỏng, sai khác hiển thị do float |

Bucket histogram là tích lũy: cùng request được đếm ở mọi bucket có ngưỡng đủ lớn, không cộng các bucket để tính số request. Một request chưa đủ để kết luận p95/p99 hoặc RPS.

Middleware dùng route template (route.path), URL không khớp gom thành unmatched, giúp giới hạn số giá trị label. Dùng URL thật sẽ tạo nhiều time series khi bot quét URL ngẫu nhiên; request_id, user_id và câu hỏi cũng không nên làm label.

Codex bổ sung Histogram agent_question_length_chars (bucket 20/50/100/200/500/1000/2000 ký tự) và observe(len(body.question)) trước retrieval. Học viên đã restart v2, gửi câu hỏi What is Docker? và cung cấp output xác nhận metric mới hoạt động: count=1, sum=15 ký tự. Tất cả bucket từ le=20 trở lên đều bằng 1, đúng với histogram tích lũy.

## AI log

### Part 1 — 25/11/2026

- Yêu cầu: nhờ Codex đọc tài liệu và hỗ trợ hoàn thành Part 1.
- AI hỗ trợ: đối chiếu code develop/production, chạy HTTP server thật, gọi API, kiểm tra shutdown khi rảnh và soạn bảng anti-patterns/so sánh dựa trên kết quả thực tế.
- Phạm vi thay đổi: thêm câu trả lời và bằng chứng Part 1; giữ nguyên code mẫu, script chấm và golden dataset.
- Đã kiểm chứng bằng công cụ: status/body của API hai bản, env PORT/ENVIRONMENT, log shutdown và lỗi cấu hình logging. Không bịa số đo.
- Học viên tự kiểm tra: đã tự chạy các lệnh Part 1 theo hướng dẫn và xác nhận kết quả đúng kỳ vọng trong chat ngày 25/11/2026. Codex cập nhật xác nhận này theo thông tin học viên cung cấp; không thay thế output đo trước bằng output mới chưa được gửi.
- AI hỗ trợ bổ sung: hướng dẫn từng lệnh chạy develop/production, kiểm tra API và đổi PORT; hỗ trợ giải phóng cổng 8000 khi bị chiếm.

### Part 2 — 25/11/2026

- AI hỗ trợ: hướng dẫn build/run/Compose, giải thích Dockerfile và lỗi Docker Hub 429; tính tỷ lệ giảm kích thước, soạn câu trả lời theo cấu hình repo.
- Học viên tự kiểm tra: đã cung cấp output hai image build thành công và hai request qua Nginx trả 200.
- Nguồn số liệu: output terminal học viên gửi, gồm docker images, curl qua Nginx và docker compose ps. Agent/Redis/Qdrant healthy, Nginx đang chạy. Đã bổ sung output curl riêng của container develop: GET /health và POST /ask đều trả 200; nội dung được chép từ output học viên gửi.

### Part 4 — Exercise 4.1 — 25/11/2026

- Học viên tự chạy và cung cấp ba response: thiếu key 401, sai key 403, đúng key 200.
- AI đối chiếu source, sửa dự đoán sai trước đó về mã lỗi của key sai, ghi đúng bằng chứng và giải thích cơ chế kiểm tra/rotate key. Chưa xác nhận JWT, rate limit hoặc cost guard.

### Part 4 — Exercise 4.2 — 25/11/2026

- Học viên gửi response POST /ask có JWT trả 200, requests_remaining=9. AI lưu output và giải thích phạm vi kiểm chứng; không thu thập hay ghi token.

### Part 4 — Exercise 4.3 và đọc cost guard — 25/11/2026

- Học viên cung cấp vòng lặp 20 request và response 429 có Retry-After: 20. AI lưu bằng chứng và đối chiếu thuật toán, quota user/admin, giới hạn state trong RAM.
- AI đọc cost_guard.py/app.py, phát hiện trường budget_remaining_usd trong /ask đang trả chi phí đã dùng; chưa chạy kiểm tra vượt budget hoặc hoàn thành phần Redis của Exercise 4.4.

### Part 4 — Exercise 4.4 — 25/11/2026

- Học viên cung cấp GET /me/usage trả 200: requests=10, input_tokens=58, output_tokens=296, cost_usd=0.000186, budget_remaining_usd=0.999814.
- AI lưu output, đối chiếu công thức và bổ sung thiết kế cost guard Redis 10 USD/tháng, gồm giữ chỗ nguyên tử và reset theo tháng. Đây là phần giải thích thiết kế; chưa thay code mẫu, chưa chạy Redis hoặc kiểm tra 402.

### Part 5 — Exercise 5.1 — 25/11/2026

- Học viên cung cấp output /health và /ready đều 200. AI lưu bằng chứng, đối chiếu middleware và psutil để giải thích đúng counter và bộ nhớ; chưa xác nhận shutdown hay stateless.

### Part 5 — Exercise 5.2 — 25/11/2026

- Học viên tự gửi request, SIGTERM và cung cấp response 200 cùng log server Finished server process [59882]. AI lưu bằng chứng shutdown, ghi rõ chưa đo exit code server và giới hạn blocking của mẫu.

### Part 5 — Exercise 5.3–5.5 — 25/11/2026

- Học viên tự chạy Compose 3 agent và test_stateless.py, gửi ps cùng output 5 request/3 instance/10 tin nhắn. AI lưu bằng chứng và giải thích state dùng chung qua Redis; không ghi nhận thử kill instance hoặc restart Redis chưa thực hiện.

### Part 6 — 25/11/2026

- AI hỗ trợ: tự triển khai 11 file TODO, chạy script chấm đầy đủ có Docker, đọc output và kiểm tra git diff --check.
- Kết quả từ công cụ: PASS 12/12, 41/41 checks; giữ nguyên script chấm và golden dataset.
- Học viên tự kiểm tra: đã chạy python check_production_ready.py (bản đầy đủ, có Docker) và gửi toàn bộ output PASS 12/12, 41/41 checks. Học viên vẫn cần đọc và giải thích được các module auth/rate limit/budget/lifecycle khi Lab Coach hỏi.

### Part 3 — 25/11/2026

- AI hướng dẫn CLI tạo project/Redis/agent, đặt env và deploy; học viên thực hiện các lệnh đăng nhập/triển khai.
- Codex gọi URL public xác nhận health 200, ready 200 và ask không key 401. Học viên cung cấp response ask đúng key 200; không chia sẻ key.
- AI tạo DEPLOYMENT.md, bổ sung so sánh cấu hình và mô tả pipeline từ source; đã bổ sung ảnh dashboard/running/test chụp trực tiếp trên Railway, không có secret.

### Part 7 — Exercise 7.1 — 25/11/2026

- Học viên chạy v1/v2 và gửi response v2 cùng metrics thật. AI lưu bằng chứng, giải thích Counter/Gauge/Histogram và cardinality, bổ sung Histogram độ dài câu hỏi. Chưa chạy load test, chưa ghi số benchmark.

### Part 7 — Xác nhận Histogram độ dài câu hỏi — 25/11/2026

- Học viên gọi /ask với What is Docker?, response agent_version=v2, input_tokens=70, output_tokens=40, cost_usd=3.45e-05, llm_latency_ms=193.7, request_id=a58570cad12c.
- Output /metrics: agent_question_length_chars_count=1.0; agent_question_length_chars_sum=15.0; bucket le=20/50/100/200/500/1000/2000/+Inf đều bằng 1.0. Codex đối chiếu độ dài 15 ký tự và lưu xác nhận; chưa có kết quả load test.

### Part 7 — Load test concurrency — 25/11/2026

- Học viên chạy 300 request ở concurrency 1/10/50/100 và gửi output; Codex đọc 4 JSON gốc, copy ra reports/ ở gốc repo, điền bảng 2.1 BENCHMARK_REPORT.md.
- Kết quả: 1/10/50 PASS, 100 FAIL p95=2209.9 ms; không thay đổi số đo. Nhận xét nêu giới hạn mẫu và chưa xác định nút thắt bằng profiling.

### Part 7 — Tail latency — 25/11/2026

- Học viên cung cấp ba lần load test slow rate 0/0.03/0.1. Codex đọc JSON, copy vào reports/ ở gốc, điền bảng 2.2 và nhận xét trong BENCHMARK_REPORT.md.
- p99 tăng mạnh ở slow rate 0.03; p95=1682.8 ms gây FAIL tại slow rate 0.1. Giữ nguyên kết quả, không sửa số đo.

### Part 7 — Eval baseline và sửa KB — 25/11/2026

- Học viên chạy eval v1/v2, gửi output. Codex đọc JSON: v1=1/23, v2=21/23, không regression. Copy hai file ra reports/, điền bảng so sánh.
- Codex bổ sung tài liệu JWT/HPA trong KB develop và production, không sửa golden dataset; chưa ghi nhận eval sau sửa.
- Thêm .github/workflows/eval.yml: khởi động v2 lỗi mô phỏng bằng 0, chờ health, chạy eval ngưỡng 85% và baseline reports/eval_v2.json. Exit code khác 0 làm job fail; để thực sự chặn merge cần bật required status check trong branch protection/ruleset. Chưa có bằng chứng workflow đã chạy trên GitHub.

### Part 7 — Eval sau sửa KB — 25/11/2026

- Học viên restart v2 và chạy eval với ngưỡng 100%, baseline eval_v2.json; kết quả 23/23, 0 errors, 0 regression, quality gate PASS.
- Codex đọc eval_v2_fixed.json, copy vào reports/ ở gốc và hoàn thiện bảng chất lượng trong BENCHMARK_REPORT.md. Cost 0.000793 USD, avg tokens 113.9, cost/câu đúng 0.00003448 USD.

### Part 7 — Sửa lỗi khởi động Docker observability

- Agent restart do ModuleNotFoundError: uvicorn. Dockerfile mẫu tạo user agent với home=/app nhưng copy thư viện --user vào /home/agent/.local. Codex thêm ENV PYTHONUSERBASE=/home/agent/.local, build lại stack.
- Kiểm tra thực tế sau sửa: agent healthy, cả 6 service đang Up, GET localhost:8080/health qua Nginx trả 200, tracing_enabled trỏ tới Jaeger. Grafana giữ host port 3000 sau khi học viên giải phóng cổng.

### Part 7 — Dashboard và tracing

- Học viên bật tải Locust và xác nhận có dữ liệu. Codex chụp giao diện Grafana/Jaeger thật, lưu 3 ảnh grafana-dashboard.png, jaeger-slow-trace.png, jaeger-error-trace.png.
- Codex đọc Jaeger API và log Docker để khớp trace_id: trace chậm 1660.117 ms, span LLM 1642.435 ms; trace lỗi HTTP 503 có exception. Bổ sung số đo/log vào BENCHMARK_REPORT.md. Alerts và scaling CSV vẫn chưa hoàn thành.

### Part 7 — Alert experiments

- Theo yêu cầu kiểm tra của học viên, Codex phát hiện agent còn fault mặc định; áp dụng error=0.2, slow=0.3 đồng thời và theo dõi API 10 giây/lần.
- AgentHighErrorRate firing sau khoảng 78 giây; AgentHighLatencyP95 sau khoảng 138 giây; ảnh chụp cả hai firing lưu screenshots/prometheus-alert-firing.png. Số chính xác theo lần quan sát ghi trong BENCHMARK_REPORT.md và reports/alert-experiment.json.
- promtool test rules: SUCCESS. Đã đủ 4 ảnh Part 7; benchmark scaling CSV và hoàn thiện kết luận còn thiếu.

### Part 7 — Benchmark scaling và hoàn thiện báo cáo — 26/11/2026

- Học viên chạy Locust headless 100 users/2 phút cho scale 1 và 3, cung cấp xác nhận CSV. Codex đọc stats/failures/stats_history, đối chiếu tổng count và failures, copy 8 file CSV ra benchmark-results/ ở gốc.
- Bảng dùng riêng POST /ask: RPS 59.83/59.75, p95 220/220 ms, p99 1700/1700 ms; phân tích giới hạn tải user đóng và mock LLM.
- Hoàn thiện bảng scaling/kết luận BENCHMARK_REPORT.md. Bộ file minh chứng local đã có đủ; chưa thực hiện commit/push hoặc nộp LMS thay học viên.
