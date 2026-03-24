# FxMail API Documentation

API documentation for frontend developers building **web mail clients** and **mobile apps**.

## Backend URL

```
https://freedomos.vulcantech.co
```

**API Base:** `https://freedomos.vulcantech.co/api/v1`

## Documents

- **[API_DOCUMENTATION.md](./API_DOCUMENTATION.md)** — Full API reference (auth, email, drive, public endpoints, errors, rate limits)

- **[DEVICE_KEY_DECRYPTION.md](./DEVICE_KEY_DECRYPTION.md)** — Client-side device key decryption spec — use this to fix "Could not decrypt device key" on login

## Quick Start

1. **Register:** `POST /api/v1/auth/register` with email, password, device_id
2. **Save** the `device_key_download` on the device (required for future logins)
3. **Login:** Use `/auth/login/challenge` then `/auth/login/secure` with device proof
4. **Send email:** `POST /api/v1/email/send` with `Authorization: Bearer <token>`
5. **Fetch inbox:** `GET /api/v1/email/inbox`

## Security

- All protected endpoints require `Authorization: Bearer <access_token>`
- Email and file content are E2E encrypted
- Device binding is required for returning users
