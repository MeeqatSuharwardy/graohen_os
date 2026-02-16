# VPS and Email API Performance

Recommendations for running the email backend (and full stack) with good response times.

## Why the email API can feel slow

1. **SMTP notifications** – After storing an email, the app sends a notification email to each recipient via SMTP. Each send can take 1–5+ seconds. We now send these in the **background**, so the send/reply API returns right after encrypt + MongoDB write.
2. **Encryption** – Multi-layer encryption (AES-256-GCM, ChaCha20-Poly1305) is CPU-bound. More CPU helps.
3. **MongoDB** – Latency depends on connection string (same VPS vs remote) and indexes. Run `scripts/setup_mongodb.py` so all recommended indexes exist.
4. **Redis** – Used for rate limiting; local Redis is fast.

## Recommended VPS configuration

| Use case              | vCPU | RAM  | Storage | Notes |
|-----------------------|------|------|---------|--------|
| **Light / dev**       | 1    | 2 GB | 20 GB   | Single app + MongoDB + Redis on one box. |
| **Production (email)**| 2    | 4 GB | 40 GB SSD | Same or separate MongoDB. Run `setup_mongodb.py` for indexes. |
| **Higher traffic**    | 4    | 8 GB | 80 GB SSD | Consider separate MongoDB/Redis if you outgrow one server. |

- **Provider examples**: DigitalOcean, Hetzner, Vultr, Linode.
- **Region**: Choose one close to your users and, if possible, to your MongoDB host.
- **SSD**: Prefer SSD for MongoDB and OS; it improves write and index performance.

## What we did in code to make it faster

- **Background notifications**: Send and reply APIs no longer wait for SMTP. They return after encrypt + store; notification emails are sent in a background task.
- **Reply API**: `POST /api/v1/email/{email_id}/reply` – reply to an email (you must be sender or recipient). Uses the same fast store path as send.

## Optional: tune for speed

- **MongoDB**: If MongoDB is on the same VPS, use `localhost` in the connection string to avoid network hops.
- **Redis**: Run Redis on the same host when possible; keep default timeout.
- **Workers**: Run 2–4 Uvicorn workers so encryption and I/O can use multiple cores (e.g. `uvicorn app.main:app --workers 2 --host 0.0.0.0`).
- **SMTP**: Use a fast, reliable SMTP provider (e.g. same region as the VPS) to keep background notification delivery quick.
