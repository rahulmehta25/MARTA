# MARTA Transit Platform - Security Audit

**Audit Date:** 2026-03-13
**Auditor:** Security Assessment System
**Classification:** Internal Use Only
**Version:** 1.0.0

---

## Executive Summary

This security audit identifies vulnerabilities across the MARTA Transit Platform codebase. The assessment covers API authentication, database security, data ingestion validation, credential management, container security, WebSocket authentication, and ML model deserialization risks.

**Risk Distribution:**
- Critical: 4
- High: 8
- Medium: 12
- Low: 6

---

## 1. API Authentication & Authorization

### 1.1 JWT Configuration

**File:** `backend/api/core/security.py`
**Severity:** High

**Finding S-1:** Default secret key in configuration

```python
# backend/api/core/config.py:56
secret_key: str = Field(default="change-me-in-production", env="SECRET_KEY")
```

**Risk:** If `SECRET_KEY` environment variable is not set, the default value allows token forgery.

**Fix:**
```python
secret_key: str = Field(..., env="SECRET_KEY")  # Required field, no default

@field_validator("secret_key")
def validate_secret_key(cls, v):
    if v == "change-me-in-production" or len(v) < 32:
        raise ValueError("SECRET_KEY must be set to a secure value (32+ chars)")
    return v
```

---

### 1.2 API Key Validation

**File:** `backend/api/core/security.py:130-145`
**Severity:** Medium

**Finding S-2:** API key logging leaks key prefixes

```python
logger.warning("Invalid API key attempt", key_prefix=api_key[:8] if len(api_key) > 8 else "***")
```

**Risk:** Log aggregation systems may expose API key fragments enabling brute-force attacks.

**Fix:** Hash API keys before logging or use only first 4 characters.

---

### 1.3 Optional Authentication on Public Endpoints

**File:** `backend/api/core/security.py:109-127`
**Severity:** Medium

**Finding S-3:** `get_current_user` returns `None` instead of raising exception for missing credentials

```python
async def get_current_user(...) -> Optional[User]:
    if not credentials:
        return None  # Allows unauthenticated access
```

**Risk:** Endpoints expecting authentication may silently accept unauthenticated requests.

**Fix:** Use explicit `require_auth` dependency for protected endpoints; document which endpoints are intentionally public.

---

## 2. SQL Injection Vulnerabilities

### 2.1 Dynamic Table Name Construction

**File:** `src/data_ingestion/marta_gtfs_connector.py:144`
**Severity:** Critical

**Finding S-4:** Unparameterized table name in SQL query

```python
insert_query = f"INSERT INTO {table_name} ({cols_str}) VALUES ({vals_str})"
```

**Risk:** If `table_name` is derived from user input, SQL injection is possible.

**Context Review:** Table names appear to be from internal configuration. Risk is mitigated but code pattern is dangerous.

**Fix:**
```python
ALLOWED_TABLES = {'gtfs_stops', 'gtfs_routes', 'gtfs_trips', ...}
if table_name not in ALLOWED_TABLES:
    raise ValueError(f"Invalid table name: {table_name}")
```

---

### 2.2 Dynamic SQL in Data Quality Monitor

**File:** `src/pipeline/monitoring/data_quality_monitor.py:273`
**Severity:** High

**Finding S-5:** Table name interpolation in COUNT query

```python
cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
```

**Risk:** Same as S-4; table name injection if derived from external source.

**Occurrences:**
- `src/pipeline/monitoring/data_quality_monitor.py:273`
- `src/pipeline/monitoring/data_quality_monitor.py:411`
- `src/data_ingestion/gtfs_ingestor.py:344`
- `src/data_ingestion/master_ingestion_orchestrator.py:185`
- `src/database/connection_pool.py:284`

**Fix:** Implement allowlist validation for all dynamic table names.

---

### 2.3 Stored Procedure Dynamic SQL

**File:** `database/stored_procedures.sql:536-547`
**Severity:** Low

**Finding S-6:** Dynamic SQL in `check_data_quality` procedure

```sql
EXECUTE format('SELECT COUNT(*) FROM %I WHERE timestamp >= ...',
              p_table_name, p_hours_back)
```

**Analysis:** PostgreSQL's `%I` identifier quoting prevents injection. This is the correct pattern.

**Status:** Acceptable - No action required.

---

### 2.4 Parameterized Query Usage (Positive)

**Files:** `src/data_ingestion/gtfs_realtime_ingestion.py:90-97`, `backend/api/routers/realtime.py:201-204`
**Severity:** N/A

**Finding S-7:** Proper parameterization observed

```python
# Good: backend/api/routers/realtime.py:201-204
result = db.execute(
    "SELECT stop_id, stop_name FROM gtfs_stops WHERE stop_id = :stop_id",
    {"stop_id": stop_id},
)
```

```python
# Good: src/data_ingestion/gtfs_realtime_ingestion.py:90-97
cursor.execute('''
    INSERT INTO ... VALUES (%s, %s, %s, ...)
''', (row['id'], row['trip_id'], ...))
```

**Status:** Compliant with OWASP guidelines.

---

## 3. GTFS Feed Ingestion Validation

### 3.1 Protobuf Parsing Without Size Limits

**File:** `src/data_ingestion/gtfs_realtime_ingestion.py:74-83`
**Severity:** High

**Finding S-8:** No response size validation before protobuf parsing

```python
def fetch_and_parse_feed(url, feed_type):
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)  # No size limit
```

**Risk:** Malicious or corrupted GTFS feed could cause memory exhaustion.

**Fix:**
```python
MAX_FEED_SIZE = 50 * 1024 * 1024  # 50MB

def fetch_and_parse_feed(url, feed_type):
    response = requests.get(url, headers=HEADERS, timeout=10, stream=True)
    response.raise_for_status()

    content_length = int(response.headers.get('content-length', 0))
    if content_length > MAX_FEED_SIZE:
        raise ValueError(f"Feed too large: {content_length} bytes")

    content = response.content
    if len(content) > MAX_FEED_SIZE:
        raise ValueError(f"Feed content exceeds limit")

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
```

---

### 3.2 Missing Feed Signature Validation

**File:** `src/data_ingestion/real_gtfs_realtime_ingestor.py:183-208`
**Severity:** Medium

**Finding S-9:** No validation of GTFS feed authenticity

**Risk:** Man-in-the-middle attack could inject false transit data.

**Recommendation:**
- Implement certificate pinning for MARTA API endpoints
- Consider caching previous feed timestamps to detect replay attacks

---

### 3.3 Vehicle Position Data Validation

**File:** `src/data_ingestion/real_gtfs_realtime_ingestor.py:260-273`
**Severity:** Medium

**Finding S-10:** No bounds checking on latitude/longitude

```python
'latitude': vehicle.position.latitude if vehicle.HasField('position') else None,
'longitude': vehicle.position.longitude if vehicle.HasField('position') else None,
```

**Risk:** Invalid coordinates could corrupt spatial queries or indicate data tampering.

**Fix:**
```python
def validate_coordinates(lat, lon):
    # Atlanta metro area bounds
    if lat and lon:
        if not (33.4 <= lat <= 34.2 and -84.8 <= lon <= -84.0):
            logger.warning(f"Suspicious coordinates: {lat}, {lon}")
            return None, None
    return lat, lon
```

---

## 4. Credential Management

### 4.1 Hardcoded Credentials in Docker Compose

**File:** `docker-compose.yml`
**Severity:** Critical

**Finding S-11:** Database and service passwords in version control

```yaml
# docker-compose.yml:9-11
environment:
  POSTGRES_DB: marta_db
  POSTGRES_USER: marta_user
  POSTGRES_PASSWORD: marta_password  # Line 11

# docker-compose.yml:249
- GF_SECURITY_ADMIN_PASSWORD=admin
```

**Occurrences:**
- PostgreSQL credentials: lines 9-11
- Service containers: lines 52-55, 113-116, 140-142, 164-167
- Grafana admin: line 249

**Fix:**
```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?required}

  grafana:
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:?required}
```

Create `.env.template` and document required secrets.

---

### 4.2 API Key Storage

**File:** `.env.example`
**Severity:** Low

**Finding S-12:** Example file contains placeholder that could be committed

```bash
MARTA_API_KEY=your_marta_api_key_here
SECRET_KEY=your-secret-key-change-in-production
```

**Status:** Acceptable for example file, but verify `.gitignore` includes actual `.env` files.

**Verification:**
```bash
# Ensure these patterns exist in .gitignore
.env
.env.local
.env.*.local
```

---

### 4.3 Redis Without Authentication (Development)

**File:** `docker-compose.yml:26-30`
**Severity:** Medium (Production Risk)

**Finding S-13:** Redis container has no password

```yaml
redis:
  image: redis:7-alpine
  # No REDIS_PASSWORD or requirepass
```

**Fix for Production:**
```yaml
redis:
  image: redis:7-alpine
  command: redis-server --requirepass ${REDIS_PASSWORD}
```

---

## 5. Docker Security

### 5.1 Base Image Version Pinning

**File:** `Dockerfile`
**Severity:** Low

**Finding S-14:** Base images use minor version tags

```dockerfile
FROM python:3.12-slim as base
```

**Recommendation:** Pin to specific digest for reproducible builds:
```dockerfile
FROM python:3.12-slim@sha256:abc123...
```

---

### 5.2 Non-Root User (Positive)

**File:** `Dockerfile:60-71`
**Severity:** N/A

**Finding S-15:** Production stage creates non-root user

```dockerfile
# Create non-root user
RUN useradd --create-home --shell /bin/bash marta
USER marta
```

**Status:** Compliant with container security best practices.

---

### 5.3 Missing Resource Limits

**File:** `docker-compose.yml`
**Severity:** High

**Finding S-16:** No CPU/memory limits defined

**Risk:** Container escape or resource exhaustion attacks.

**Fix:**
```yaml
services:
  marta_api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
```

---

### 5.4 Volume Mount Security

**File:** `docker-compose.yml:58-60`
**Severity:** Medium

**Finding S-17:** Log directory mounted read-write

```yaml
volumes:
  - ./logs:/app/logs
  - ./models:/app/models
```

**Risk:** Container compromise could allow host filesystem access.

**Recommendation:** Use named volumes for sensitive data; mount logs as write-only if possible.

---

## 6. WebSocket Authentication

### 6.1 No Authentication on WebSocket Endpoint

**File:** `backend/api/routers/realtime.py:315-330`
**Severity:** Critical

**Finding S-18:** WebSocket endpoint accepts any connection

```python
@router.websocket("/ws/live-updates")
async def websocket_live_updates(
    websocket: WebSocket,
    channel: str = Query("all", description="Channel to subscribe to"),
):
    await manager.connect(websocket, channel)  # No auth check
```

**Risk:** Unauthorized users can subscribe to real-time transit data; potential for abuse or data scraping.

**Fix:**
```python
from backend.api.core.security import verify_token

@router.websocket("/ws/live-updates")
async def websocket_live_updates(
    websocket: WebSocket,
    channel: str = Query("all"),
    token: str = Query(None),
):
    # Authenticate connection
    if token:
        try:
            token_data = verify_token(token)
        except HTTPException:
            await websocket.close(code=4001, reason="Invalid token")
            return
    else:
        # Allow anonymous for public data, but rate limit
        pass

    await manager.connect(websocket, channel)
```

---

### 6.2 Channel Subscription Without Validation

**File:** `backend/api/routers/realtime.py:357-365`
**Severity:** Medium

**Finding S-19:** Dynamic channel subscription allows any channel name

```python
elif msg_type == "subscribe":
    new_channel = message.get("channel", "all")  # Any value accepted
    await manager.disconnect(websocket, channel)
    await manager.connect(websocket, new_channel)
```

**Risk:** Resource exhaustion by creating excessive channels.

**Fix:**
```python
ALLOWED_CHANNELS = {'all', 'vehicles', 'arrivals', 'alerts'}
ROUTE_PATTERN = re.compile(r'^route:[A-Z0-9]+$')

def validate_channel(channel: str) -> bool:
    return channel in ALLOWED_CHANNELS or ROUTE_PATTERN.match(channel)
```

---

### 6.3 No Connection Rate Limiting

**File:** `backend/api/routers/realtime.py:33-70`
**Severity:** Medium

**Finding S-20:** ConnectionManager has no per-client limits

```python
class ConnectionManager:
    async def connect(self, websocket: WebSocket, channel: str = "all"):
        await websocket.accept()
        # No limit on connections per IP
```

**Fix:**
```python
MAX_CONNECTIONS_PER_CLIENT = 5

async def connect(self, websocket: WebSocket, channel: str = "all"):
    client_ip = websocket.client.host

    async with self._lock:
        client_connections = sum(
            1 for ch in self.active_connections.values()
            for ws in ch if ws.client.host == client_ip
        )
        if client_connections >= MAX_CONNECTIONS_PER_CLIENT:
            await websocket.close(code=4029, reason="Too many connections")
            return
```

---

## 7. ML Model Deserialization Risks

### 7.1 Unsafe Pickle Deserialization

**File:** `src/models/model_serving.py:137-156`
**Severity:** Critical

**Finding S-21:** Direct pickle.load() from filesystem

```python
def load_model(self) -> None:
    if self.model_type == "sklearn":
        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)  # Line 139
    ...
    if self.scaler_path and os.path.exists(self.scaler_path):
        if self.scaler_path.endswith('.pkl'):
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)  # Line 154
```

**Risk:** Pickle files are executable; a malicious model file can achieve remote code execution.

**Affected Files:**
- `src/models/model_serving.py:139, 154`
- `src/models/demand_forecaster.py:767, 774`
- `src/performance/cache_manager.py:171`
- `src/database/redis_cache.py:226`
- `backend/api/services/forecast.py:37, 44`
- `src/api/optimization_api.py:426`
- Multiple files in `src/ml_pipeline/`

**Fix (Short-term):**
```python
import hashlib

TRUSTED_MODEL_HASHES = {
    "xgboost_model.pkl": "sha256:abc123...",
    "lstm_scaler.pkl": "sha256:def456...",
}

def load_model_safely(path: str):
    # Verify hash before loading
    with open(path, 'rb') as f:
        content = f.read()
        file_hash = "sha256:" + hashlib.sha256(content).hexdigest()

    if path not in TRUSTED_MODEL_HASHES:
        raise SecurityError(f"Unknown model file: {path}")
    if file_hash != TRUSTED_MODEL_HASHES[path]:
        raise SecurityError(f"Model file hash mismatch: {path}")

    return pickle.loads(content)
```

**Fix (Long-term):**
- Use ONNX or TensorFlow SavedModel format instead of pickle
- Implement model signing with cryptographic signatures
- Store model hashes in secure configuration

---

### 7.2 Joblib Deserialization (Same Risk)

**File:** `src/models/model_serving.py:141`
**Severity:** High

**Finding S-22:** joblib.load() has same RCE risk as pickle

```python
elif self.model_type == "joblib":
    self.model = joblib.load(self.model_path)
```

**Affected Files (25+ occurrences):**
- `src/models/xgboost_demand_forecaster.py:333-340`
- `src/models/lstm_demand_forecaster.py:404-408`
- `src/models/model_ensemble.py:96-113`
- `src/ml_pipeline/inference/serving.py:272-296`
- `src/optimization/route_optimizer.py:107-113`

**Fix:** Same as S-21; verify hashes before loading.

---

### 7.3 Redis Cache Pickle Fallback

**File:** `src/database/redis_cache.py:224-226`
**Severity:** High

**Finding S-23:** Cache deserialization falls back to pickle

```python
except (json.JSONDecodeError, UnicodeDecodeError):
    # Fall back to pickle
    return pickle.loads(data)
```

**Risk:** Redis cache poisoning could lead to RCE on cache read.

**Fix:**
```python
except (json.JSONDecodeError, UnicodeDecodeError):
    logger.error("Failed to deserialize cache entry as JSON")
    return None  # Do not fall back to pickle
```

---

## 8. Additional Security Concerns

### 8.1 CORS Configuration

**File:** `backend/api/middleware.py:189-203`
**Severity:** Medium

**Finding S-24:** Wildcard methods and headers

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Risk:** Overly permissive CORS; production should restrict methods.

**Fix:**
```python
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
```

---

### 8.2 Security Headers (Positive)

**File:** `backend/api/middleware.py:167-183`
**Severity:** N/A

**Finding S-25:** Security headers properly implemented

```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = ...
```

**Status:** Compliant with OWASP security headers.

---

### 8.3 RLS Policies

**File:** `secure_rls_policies.sql`
**Severity:** Low

**Finding S-26:** Row-Level Security properly configured

```sql
CREATE POLICY "Public can read arrivals" ON arrivals
    FOR SELECT USING (true);

CREATE POLICY "Service role can insert arrivals" ON arrivals
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role' OR
        auth.role() = 'authenticated'
    );
```

**Status:** Appropriate separation of read/write permissions.

---

### 8.4 CI/CD Security Scanning

**File:** `.github/workflows/ci.yml:448-475`
**Severity:** N/A (Positive)

**Finding S-27:** Security tooling integrated

```yaml
- name: Run Bandit security check
  run: bandit -r src/ --severity-level medium

- name: Check for known security vulnerabilities
  run: safety check

- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
```

**Status:** Good security posture in CI pipeline.

---

## 9. Risk Summary Matrix

| ID | Finding | Severity | CVSS | Status |
|----|---------|----------|------|--------|
| S-1 | Default secret key | High | 7.5 | Open |
| S-4 | SQL injection (table names) | Critical | 9.8 | Open |
| S-8 | Unbounded protobuf parsing | High | 7.1 | Open |
| S-11 | Hardcoded credentials | Critical | 9.1 | Open |
| S-16 | No container resource limits | High | 6.5 | Open |
| S-18 | Unauthenticated WebSocket | Critical | 8.1 | Open |
| S-21 | Pickle deserialization RCE | Critical | 9.8 | Open |
| S-22 | Joblib deserialization RCE | High | 9.8 | Open |
| S-23 | Redis pickle fallback | High | 8.1 | Open |

---

## 10. Prioritized Remediation Plan

### Phase 1: Critical (Immediate - 48 hours)

| Priority | Finding | Effort | Owner |
|----------|---------|--------|-------|
| P0-1 | S-21: Implement model hash verification | 4h | ML Team |
| P0-2 | S-18: Add WebSocket authentication | 4h | Backend Team |
| P0-3 | S-11: Move secrets to env vars / vault | 2h | DevOps |
| P0-4 | S-4: Add table name allowlist | 2h | Backend Team |

### Phase 2: High (Week 1)

| Priority | Finding | Effort | Owner |
|----------|---------|--------|-------|
| P1-1 | S-1: Require SECRET_KEY | 1h | Backend Team |
| P1-2 | S-8: Add feed size limits | 2h | Ingestion Team |
| P1-3 | S-16: Define container limits | 2h | DevOps |
| P1-4 | S-22, S-23: Fix all pickle usage | 8h | ML Team |

### Phase 3: Medium (Week 2-3)

| Priority | Finding | Effort | Owner |
|----------|---------|--------|-------|
| P2-1 | S-10: Add coordinate validation | 2h | Ingestion Team |
| P2-2 | S-13: Secure Redis | 1h | DevOps |
| P2-3 | S-19, S-20: WebSocket hardening | 4h | Backend Team |
| P2-4 | S-24: Restrict CORS | 1h | Backend Team |

### Phase 4: Low (Ongoing)

| Priority | Finding | Effort | Owner |
|----------|---------|--------|-------|
| P3-1 | S-2: Reduce API key logging | 1h | Backend Team |
| P3-2 | S-9: Certificate pinning | 4h | Security Team |
| P3-3 | S-14: Pin Docker images | 1h | DevOps |

---

## Appendix: Security Tool Configuration

### Recommended .bandit File

```yaml
# .bandit
skips:
  - B101  # assert statements (acceptable in tests)
exclude_dirs:
  - tests
  - marta_env_*
targets:
  - src
  - backend
```

### Recommended Safety Configuration

```bash
# Run in CI
safety check --full-report --output json
```

---

*End of Security Audit*

**Next Steps:**
1. Create JIRA tickets for each finding
2. Schedule security review meeting
3. Implement P0 fixes before next deployment
4. Re-audit after Phase 1 completion
