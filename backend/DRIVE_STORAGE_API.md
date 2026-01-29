# Drive Storage Usage API

The Drive API exposes an endpoint that returns **how much storage is used** out of the **total allocated** (quota) for the current user.

---

## Endpoint

| Method | Path | Auth |
|--------|------|------|
| **GET** | `/api/v1/drive/storage/quota` | Bearer token (required) |

**Full URL (example):**  
`https://your-backend.com/api/v1/drive/storage/quota`

---

## Response

**200 OK** – JSON body:

```json
{
  "used_bytes": 1073741824,
  "quota_bytes": 5368709120,
  "used_gb": 1.0,
  "quota_gb": 5.0,
  "available_bytes": 4294967296,
  "available_gb": 4.0,
  "percentage_used": 20.0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `used_bytes` | int | Storage used in bytes |
| `quota_bytes` | int | Total allocated (quota) in bytes (default 5 GB) |
| `used_gb` | float | Used in GB (rounded to 2 decimals) |
| `quota_gb` | float | Quota in GB (rounded to 2 decimals) |
| `available_bytes` | int | Remaining bytes (`quota_bytes - used_bytes`) |
| `available_gb` | float | Remaining GB |
| `percentage_used` | float | Used percentage (0–100) |

---

## How to Call

### 1. cURL

```bash
curl -X GET "https://your-backend.com/api/v1/drive/storage/quota" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Replace `YOUR_ACCESS_TOKEN` with a valid JWT from your auth/login endpoint.

### 2. JavaScript (fetch)

```javascript
const response = await fetch('https://your-backend.com/api/v1/drive/storage/quota', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  },
});

if (!response.ok) throw new Error(`HTTP ${response.status}`);
const data = await response.json();

console.log(`Used: ${data.used_gb} GB / ${data.quota_gb} GB (${data.percentage_used}%)`);
console.log(`Available: ${data.available_gb} GB`);
```

### 3. Python (requests)

```python
import requests

url = "https://your-backend.com/api/v1/drive/storage/quota"
headers = {"Authorization": f"Bearer {access_token}"}

r = requests.get(url, headers=headers)
r.raise_for_status()
data = r.json()

print(f"Used: {data['used_gb']} GB / {data['quota_gb']} GB ({data['percentage_used']}%)")
print(f"Available: {data['available_gb']} GB")
```

---

## Errors

| Status | Meaning |
|--------|--------|
| **401 Unauthorized** | Missing or invalid Bearer token |
| **500 Internal Server Error** | Server error (e.g. Redis/MongoDB) |

---

## Notes

- **Quota** is per user (by email). Default is **5 GB**; can be overridden per user via Redis key `drive:storage:{user_email}:quota`.
- **Used** is the sum of sizes of all files owned by the user (tracked in Redis `drive:storage:{user_email}` and updated on upload/delete).
- The endpoint is implemented in `app/api/v1/endpoints/drive.py` as `get_storage_quota`.
