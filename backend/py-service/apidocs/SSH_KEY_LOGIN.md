# SSH Key Login – Server Implementation

## Overview

SSH key login provides **browser-only** authentication. No `device_id` is required. Designed for web clients; device-bound auth remains for mobile.

- **Storage:** SSH public keys are stored **encrypted** at rest using AES-256-GCM.
- **Decryption:** Happens only in-memory during signature verification. No one can decrypt without the server's `SECRET_KEY`.
- **Encryption key:** Derived from `SECRET_KEY` via SHA-256 (domain: `ssh-key-encryption:v1`).

---

## Flow

1. User generates Ed25519 (or RSA) key pair in browser.
2. User uploads public key at registration (`ssh_public_key`) or via `POST /auth/ssh-key/add`.
3. Server encrypts and stores public key in `user_ssh_keys` table.
4. For login:
   - `POST /auth/login/ssh/challenge` → server returns challenge, stores it in Redis (2 min TTL).
   - Client signs challenge with private key.
   - `POST /auth/login/ssh` → server decrypts stored key, verifies signature, issues tokens.

---

## Decryption Manager

The decryption logic lives in `app/services/ssh_key_service.py`:

- `decrypt_ssh_public_key(encrypted_payload)` – decrypts stored key for verification.
- Called only from `verify_ssh_signature()` during login.
- Decrypted key is never persisted or exposed; used only for `public_key.verify()`.

---

## Supported Key Types

- **Ed25519** (recommended)
- **RSA** (PKCS1v15, SHA-256)
- **ECDSA** (P-256, P-384, P-521)

---

## Database

Table: `user_ssh_keys`

| Column              | Type    | Description                          |
|---------------------|---------|--------------------------------------|
| id                  | int     | Primary key                          |
| user_id             | int     | FK to users                          |
| key_fingerprint     | string  | SHA256 of public key (hex), unique   |
| encrypted_public_key| text    | JSON `{ciphertext, nonce, tag}`      |
| key_type            | string  | ed25519, rsa, ecdsa                  |
| created_at          | datetime|                                      |
| updated_at          | datetime|                                      |

---

*Last updated: March 2026*
