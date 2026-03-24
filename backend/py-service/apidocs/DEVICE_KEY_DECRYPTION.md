# Device Key Decryption – Client Implementation Guide

This document specifies **exactly** how to decrypt `device_key_download` on the client (web/mobile). Mismatches cause "Could not decrypt device key" even with the correct password.

---

## Blob Format

`device_key_download` from register/device-key/download:

```json
{
  "ciphertext": "base64-encoded",
  "nonce": "base64-encoded",
  "tag": "base64-encoded",
  "salt": "base64-encoded"
}
```

**Important:** `salt` is required. Do not skip it.

---

## Decryption Steps (Client-Side)

### 1. Key Derivation (Argon2id)

The encryption key is derived from **password + salt** using Argon2id.

**Parameters (must match server exactly):**

| Parameter   | Value | Notes                    |
|------------|-------|---------------------------|
| Algorithm  | Argon2id | Type.ID in argon2    |
| memory_cost| 65536 | 64 MiB (2^16 KB)          |
| time_cost  | 3     | Iterations                |
| parallelism| 1    | Threads                    |
| hash_len   | 32    | Output key size (bytes)   |
| version    | 0x13 (19) | Argon2 1.3           |

**Inputs:**

- `passcode`: user password as **UTF-8** string
- `salt`: **base64-decode** the `salt` field from the blob

**JavaScript (argon2-browser or @noble/hashes):**

```javascript
// Using argon2-browser
import argon2 from 'argon2-browser';

const salt = Uint8Array.from(atob(blob.salt), c => c.charCodeAt(0));
const key = await argon2.hash({
  pass: new TextEncoder().encode(password),
  salt,
  time: 3,
  mem: 65536,
  hashLen: 32,
  parallelism: 1,
  type: argon2.ArgonType.Argon2id,
});
// key.hash is Uint8Array of 32 bytes
```

**Python (server reference):**

```python
from argon2.low_level import hash_secret_raw, Type

derived_key = hash_secret_raw(
    secret=password.encode("utf-8"),
    salt=salt_bytes,
    time_cost=3,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    type=Type.ID,  # Argon2id
    version=19,
)
```

---

### 2. AES-256-GCM Decryption

**Parameters:**

- Algorithm: AES-256-GCM
- Nonce: 12 bytes (base64-decode `nonce`)
- Tag: 16 bytes (base64-decode `tag`)
- Ciphertext: base64-decode `ciphertext`

**GCM input:** `ciphertext + tag` concatenated (ciphertext first, then tag).

**JavaScript (Web Crypto):**

```javascript
const key = await crypto.subtle.importKey(
  'raw',
  derivedKeyBytes,
  { name: 'AES-GCM' },
  false,
  ['decrypt']
);

const ciphertext = Uint8Array.from(atob(blob.ciphertext), c => c.charCodeAt(0));
const tag = Uint8Array.from(atob(blob.tag), c => c.charCodeAt(0));
const nonce = Uint8Array.from(atob(blob.nonce), c => c.charCodeAt(0));

// GCM: ciphertext || tag
const ciphertextWithTag = new Uint8Array(ciphertext.length + tag.length);
ciphertextWithTag.set(ciphertext);
ciphertextWithTag.set(tag, ciphertext.length);

const seed = await crypto.subtle.decrypt(
  { name: 'AES-GCM', iv: nonce, tagLength: 128 },
  key,
  ciphertextWithTag
);
```

---

## Common Causes of "Could not decrypt device key"

### 1. Missing or wrong salt

- The blob includes `salt`; the client must use it for Argon2.
- If the client uses a fixed or wrong salt, decryption will fail.

### 2. Password encoding / trimming

- Use UTF-8: `password` → `new TextEncoder().encode(password)`.
- Avoid trimming unless the backend does the same.
- Be careful with autofill or copy-paste (invisible chars, extra spaces).

### 3. Argon2 parameters mismatch

- Any difference in `memory_cost`, `time_cost`, `parallelism`, `hash_len`, `type`, or `version` yields a different key.
- Ensure the client uses exactly the values above.

### 4. GCM ciphertext/tag order

- Server stores ciphertext and tag separately but concatenates them for decryption.
- Order must be: `ciphertext || tag` (ciphertext first, tag last).

### 5. Base64 decoding

- Ensure no extra whitespace and correct base64 alphabet (including padding if required).

### 6. Corrupted stored blob

- If `device_key_download` is stored (e.g. in localStorage), it can be corrupted or truncated.
- Log and verify the stored blob structure and length.

### 7. Wrong blob source

- Use the blob returned at registration (or from device-key/download).
- Do not confuse with another encrypted payload from the API.

---

## Fallback: Device Key Download

If decryption keeps failing, the user can fetch a fresh blob using their password:

```
POST /api/v1/auth/device-key/download
{
  "email": "user@fxmail.ai",
  "password": "correct-password",
  "device_id": "same-device-id-used-at-registration"
}
```

Response: new `device_key_download` encrypted with the same password. Store it and retry decryption. If this works, the old stored blob was likely corrupted or wrong.

---

## Verification Checklist (Client)

- [ ] Use `salt` from blob for Argon2
- [ ] Argon2id: memory=65536, time=3, parallelism=1, hash_len=32
- [ ] Password encoded as UTF-8
- [ ] Decrypt with ciphertext+tag order
- [ ] Nonce = 12 bytes, tag = 16 bytes
- [ ] No trimming/alteration of password unless intentional
