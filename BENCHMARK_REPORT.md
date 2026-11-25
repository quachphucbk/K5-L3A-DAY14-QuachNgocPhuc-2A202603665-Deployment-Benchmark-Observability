# Benchmark & Observability Report — Day 14

> Số liệu lấy từ JSON/CSV và ảnh thực tế đính kèm; giữ nguyên các lần SLO FAIL để phân tích.

**Họ tên:** Quách Ngọc Phúc
**Ngày chạy:** 25–26/11/2026 (GMT+7)
**Môi trường:** macOS, chạy agent v2 bằng Python local tại localhost:8002; cấu hình phần cứng và tài nguyên Docker chưa ghi nhận. Concurrency test: MOCK_ERROR_RATE=0.01, MOCK_SLOW_RATE=0.03 theo lệnh đã hướng dẫn; JSON không tự lưu các biến fault injection.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng benchmark của lab, bảo vệ phần lớn request khỏi chờ lâu. |
| Error rate `/ask` | ≤ 2% | Cho phép mức lỗi mô phỏng nhỏ, đối chiếu tỷ lệ thực tế mỗi lần chạy. |
| Accuracy trên golden dataset | ≥ 85%, không regression; sau sửa KB đạt 100% | Quality gate CI theo Exercise 7.3; mục tiêu hoàn thiện bài là 23/23. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.24 | 192.9 | 220.3 | 1705.2 | 1.33% | PASS |
| 10 | 40.74 | 192.9 | 221.7 | 1709.0 | 1.67% | PASS |
| 50 | 104.84 | 193.4 | 243.6 | 1713.5 | 0.67% | PASS |
| 100 | 75.43 | 269.5 | 2209.9 | 2423.8 | 1.00% | FAIL (p95) |

**Nhận xét:** RPS không tăng tuyến tính trên toàn dải: 4.24 → 40.74 → 104.84 → 75.43 khi concurrency 1 → 10 → 50 → 100. Mức 50 có throughput cao nhất trong bốn lần đo. Khi tăng 50 lên 100, RPS giảm khoảng 28.05% và p95 tăng từ 243.6 lên 2209.9 ms (khoảng 9.07 lần), làm vi phạm SLO latency; error rate cả bốn lần vẫn đạt ngưỡng 2%.

Mức 1–50 có p50 khoảng 193 ms nhưng p99 khoảng 1.7 giây, thể hiện tail latency. Concurrency cao có thể làm tăng tranh chấp tài nguyên, chờ kết nối hoặc lịch chạy tác vụ ở client/server; chưa có profiling nên không kết luận nút thắt cụ thể. Mỗi lần chỉ 300 request, mức 50/100 chạy chưa đến 4 giây và fault injection ngẫu nhiên; kết quả không chứng minh năng lực tải bền vững hoặc concurrency tối ưu tuyệt đối. Giữ nguyên lần FAIL để phân tích, không thay số bằng kết quả chọn lọc.

Nguồn: reports/load_v2_c1.json, load_v2_c10.json, load_v2_c50.json, load_v2_c100.json. Các file này là bản copy nguyên từ develop/reports/.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 188.9 | 217.3 | 235.5 |
| 0.03 (mặc định) | 223.1 | 215.5 | 1695.9 |
| 0.1 | 330.9 | 1682.8 | 1705.8 |

**Nhận xét:** Ba lần đều 300 request, concurrency 20, MOCK_ERROR_RATE=0.01 theo hướng dẫn; slow rate lần lượt 0/0.03/0.1 do học viên restart server. JSON lưu số đo, không tự xác nhận các env.

Khi slow rate tăng 0 → 0.03, avg tăng 188.9 → 223.1 ms (khoảng 18.1%) nhưng p99 tăng 235.5 → 1695.9 ms (khoảng 7.2 lần). p95 vẫn gần 216 ms vì nhóm request chậm hiếm chưa chiếm tới 5% trong mẫu. Khi slow rate=0.1, p95 tăng lên 1682.8 ms và vi phạm SLO 500 ms, dù avg mới 330.9 ms và p50=192.3 ms. Do đó avg che giấu trải nghiệm nhóm chậm; p99 nhạy với tail hiếm, p95 phản ánh tail khi tỷ lệ request chậm lớn hơn.

Cả ba error rate đều dưới ngưỡng 2% (0.67%/1%/1%); hai lần đầu SLO PASS, lần 0.1 FAIL do p95. Những thay đổi nhỏ như p95 217.3 → 215.5 ms có thể do ngẫu nhiên, không phải slow rate cao hơn làm nhanh hơn. Các lượt thử ngắn, chỉ dùng để minh họa; không suy ra độ ổn định lâu dài.

Nguồn: reports/load_v2_slow_0.json, load_v2_slow_0.03.json, load_v2_slow_0.1.json, copy nguyên từ develop/reports/.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.35% | 91.30% | 100.00% (23/23) |
| Avg tokens / câu | 56.6 | 109.0 | 113.9 |
| Tổng cost (USD) | 0.000397 | 0.000759 | 0.000793 |
| Cost / câu đúng (USD) | 0.00039735 | 0.00003616 | 0.00003448 |
| Quality gate | FAIL (ngưỡng 80%) | PASS (ngưỡng 80%, không regression) | PASS (ngưỡng 100%, không regression) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm tài liệu JWT so sánh API key, xác minh chữ ký và thời hạn token. |
| scaling-03 | cpu, memory, custom metrics | Thêm tài liệu Kubernetes HPA scale pod theo CPU, memory hoặc custom metrics. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

V1 đạt 1/23, v2 đạt 21/23: cải thiện 20 câu, không regression. Avg tokens tăng 56.6 → 109.0, tổng cost tăng 0.000397 → 0.000759 USD, nhưng cost/câu đúng giảm từ 0.00039735 xuống 0.00003616 USD (khoảng 11 lần). Retrieval thêm context giúp chất lượng tăng với chi phí/token mỗi request cao hơn. p95 của hai lượt eval là 184.5 và 217.5 ms; 23 câu quá ít để kết luận hiệu năng, dùng load test ở mục 2 để đánh giá latency.

Hai entry đã bổ sung ở đầu KNOWLEDGE_BASE để ưu tiên khi keyword match hòa điểm, ở cả develop và production. Học viên đã restart v2 và chạy eval fixed: 23/23, accuracy 100%, không regression, lỗi upstream 0. Avg tokens tăng 109.0 → 113.9 và cost tăng 0.000759 → 0.000793 USD; cost/câu đúng giảm xuống 0.00003448 USD. Golden dataset không sửa. Nguồn: reports/eval_v1.json, eval_v2.json và eval_v2_fixed.json.

Job CI trong .github/workflows/eval.yml khởi động v2 với MOCK_ERROR_RATE=0, đợi /health rồi chạy eval --min-accuracy 0.85 --baseline ../../../reports/eval_v2.json. Exit code 1 khi accuracy thấp hoặc regression làm job fail. Cần cấu hình required status check để chặn merge; chưa ghi nhận job đã chạy trên GitHub.

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [x] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals) — [ảnh](screenshots/grafana-dashboard.png)
- [x] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian) — [ảnh](screenshots/jaeger-slow-trace.png)
- [x] Một trace lỗi trong Jaeger (có event `exception`) — [ảnh](screenshots/jaeger-error-trace.png)
- [x] Trang Alerts của Prometheus với ít nhất 2 alert cùng đang **firing** — [ảnh](screenshots/prometheus-alert-firing.png)

**Quan sát Exercise 7.4:** dashboard đang có tải, 1 instance, traffic khoảng 18.3 req/s, error rate khoảng 0.60%, p95 khoảng 293.58 ms tại thời điểm đọc UI (số live có thể thay đổi giữa đọc/chụp). Biểu đồ p99 cao hơn avg cho thấy một nhóm request chậm mà trung bình che giấu. Chưa đọc một giá trị avg chính xác từ panel nên không bịa số. Input token/s thường lớn hơn output vì prompt có system prompt, câu hỏi và context retrieval. Với 1 instance chưa đánh giá được độ cân bằng giữa nhiều instance; thực hiện ở benchmark scale 1/3. Nginx cố ý chặn /metrics ra ngoài, Prometheus scrape agent trực tiếp qua mạng nội bộ.

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | AgentHighErrorRate | ~78.2 s | Error rate |
| B | `MOCK_SLOW_RATE=0.3` | AgentHighLatencyP95 | ~138.2 s | Latency p95/p99 |
| C | `LLM_MODEL=mock-llm-large` | Chưa thực hiện | — | — |
| D | `docker pause` 1 instance | Chưa thực hiện | — | — |
| E | `AGENT_VERSION=v1` | Chưa thực hiện trên stack; phân tích bên dưới | — | — |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

Metric hạ tầng không đảm bảo câu trả lời đúng: v1 có thể trả HTTP 200 nhanh nhưng accuracy thấp. Cần eval định kỳ trên golden dataset, quality gate trước release, theo dõi chất lượng/câu trả lời theo phiên bản và lấy phản hồi người dùng. Kết quả eval local đã cho thấy v1=1/23 dù request không lỗi.

A và B được áp dụng đồng thời trên agent lab, giữ Locust 30 users; đây không phải thí nghiệm cô lập từng biến. Đồng hồ bắt đầu sau khi Compose recreate/start xong, đọc API mỗi 10 giây nên thời gian là lần đầu quan sát firing với độ phân giải khoảng 10 giây. Agent nhận error=0.2, slow=0.3 đã được kiểm tra bằng env trong container. Alert lỗi cần for=1m, latency cần for=2m, ngoài thời gian scrape/evaluate và cửa sổ rate. Trước khi áp dụng có alert chi phí riêng, không tính nó là kết quả thí nghiệm đổi model. Bằng chứng observations: reports/alert-experiment.json.

Unit test alert rules chạy bằng promtool với file prometheus/alert_rules_test.yml: SUCCESS. Không sửa ngưỡng rule để lấy firing.

### 4.3 Debug bằng trace

Chọn một trace chậm quan sát được (không khẳng định là chậm nhất toàn bộ dữ liệu):

- `trace_id`: c7fa186ee7ff72c8bb78d22920e91a44
- Tổng thời gian: 1660.117 ms (duration span POST /ask từ Jaeger API).
- Bước nghiệp vụ chiếm thời gian chủ yếu: chat mock-llm-small (1642.435 ms, 98.93% tổng trace). Các span cha bao gồm thời gian span con, không cộng duration cha/con.
- Dòng log tương ứng (grep theo `trace_id`):

```json
{"ts": "2026-11-25T16:57:34.734801+00:00", "level": "INFO", "service": "observable-agent", "instance": "44d92299156a", "event": "llm_call", "trace_id": "c7fa186ee7ff72c8bb78d22920e91a44", "span_id": "3ed569fd70e28ee1", "request_id": "32b76400728a", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 74, "output_tokens": 37, "cost_usd": 3.3e-05, "llm_ms": 1640.9}
```

---

**Trace lỗi:** b36dbc10b114e8fa4bb9503148ffb096, tổng 117.731 ms, HTTP 503; span chat mock-llm-small có event exception, type utils.mock_llm.LLMError, message Upstream LLM error: 503 Service Unavailable (mock). Log tương ứng:

```json
{"ts": "2026-11-25T16:57:32.335948+00:00", "level": "INFO", "service": "observable-agent", "instance": "44d92299156a", "event": "llm_error", "trace_id": "b36dbc10b114e8fa4bb9503148ffb096", "span_id": "b4715d7bb759ccbc", "request_id": "3b9bf7a3cbe1", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

Ảnh trace lỗi hiển thị event exception và stack trace; ảnh trace chậm hiển thị waterfall và span LLM. Bằng chứng JSON gốc: reports/trace-slow.json và reports/trace-error.json. Thời gian UI làm tròn giây, báo cáo dùng duration microsecond của Jaeger API chuyển sang ms.

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 59.83 | 190 | 220 | 1700 | 66/7138 (0.92%) |
| 3 | 59.75 | 190 | 220 | 1700 | 79/7129 (1.11%) |

**Giải thích kết quả:** Lấy hàng POST /ask trong CSV, không dùng Aggregated vì nó trộn GET /health. Với 100 users, ramp-up 10 users/s, 2 phút, RPS 59.83 → 59.75 khi scale 1 → 3; p50/p95/p99 giữ nguyên 190/220/1700 ms theo histogram làm tròn của Locust. Hai lần có 66/7138 (0.92%) và 79/7129 (1.11%) request /ask lỗi; file failures ghi toàn HTTP 503, phù hợp mock error rate 1%.

Scale không cải thiện p95 trong tải này. Locust dùng mô hình user đóng: mỗi user đợi response và nghỉ ngẫu nhiên 0.5–2 giây giữa task. Với số user cố định và một instance đã xử lý được tải, thêm instance không buộc RPS tăng gấp ba. Cả hai lần vẫn chịu latency/tail mô phỏng của LLM; trace đã cho thấy request chậm chủ yếu ở span LLM. Chưa có profiling CPU/network hoặc bài đo cực đại, nên không khẳng định nút thắt phần cứng cụ thể hay scale không có ích ở tải cao hơn.

Số Aggregated để đối chiếu: 1 instance 65.68 req/s (7836 request), 3 instance 65.65 req/s (7832 request), gồm health check. stats_history ghi ramp-up tới 100 users; failures có thời gian UTC tương ứng 00:10–00:16 ngày 26/11/2026 GMT+7. Tên file scale_1/scale_3 và các lệnh học viên thực hiện xác định cấu hình; CSV stats tự nó không lưu số replica.

Nguồn: benchmark-results/scale_1_stats.csv và scale_3_stats.csv; nộp kèm failures/stats_history/exceptions để đối chiếu. Giữ nguyên file gốc.

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. Average có thể che giấu tail latency: ở slow rate 0.1, avg 330.9 ms nhưng p95 1682.8 ms, làm vi phạm SLO.
  2. Chất lượng và chi phí cần đo cùng nhau: v2 sau sửa đạt 23/23, cost/câu đúng 0.00003448 USD; HTTP 200 hoặc dashboard xanh không chứng minh câu trả lời đúng.
  3. Metrics báo dấu hiệu, trace tìm bước gây chậm, log có trace_id giúp đối chiếu; alert cần for và tải liên tục để tránh báo động vì spike ngắn.
- Nếu đưa agent này lên production thật, bổ sung eval chất lượng theo phiên bản, tỷ lệ câu trả lời không đạt, chi phí/câu đúng, token budget và synthetic check từ bên ngoài. Đo lỗi/latency tại Nginx để thấy 504 mà agent chưa ghi nhận, theo dõi CPU/RAM/queue để đánh giá saturation và cấu hình sampling/retention cho traces.
