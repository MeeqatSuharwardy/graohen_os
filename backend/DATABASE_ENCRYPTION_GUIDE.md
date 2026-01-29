# Database Encryption Guide

This guide explains how user data is encrypted and stored in the database.

## 🔐 Encryption Overview

All sensitive user data (email, full_name) is encrypted at rest using **multi-layer encryption** before being stored in PostgreSQL.

### Encryption Layers

1. **Layer 1**: AES-256-GCM with primary key
2. **Layer 2**: ChaCha20-Poly1305 with secondary key  
3. **Layer 3**: AES-256-GCM with Scrypt-derived key

This makes decryption extremely difficult even if one layer is compromised.

## 📊 Database Schema

### Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    encrypted_email BYTEA NOT NULL UNIQUE,  -- Encrypted email
    email_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash for lookup
    hashed_password VARCHAR(255) NOT NULL,  -- Bcrypt hashed password
    encrypted_full_name BYTEA,              -- Encrypted full name (optional)
    encryption_metadata TEXT,                -- JSON metadata for decryption
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email_hash ON users(email_hash);
```

## 🔑 Encryption Keys

### Master Key

- Derived from `SECRET_KEY` in `.env`
- Used to encrypt user-specific encryption keys
- Never stored in database

### User Keys

- Each user has unique `primary_key` and `secondary_key`
- Keys are encrypted with master key before storage
- Stored in `encryption_metadata` field

## 📝 How It Works

### Registration Flow

1. User submits email, password, full_name
2. **Email encryption:**
   - Generate unique encryption keys
   - Encrypt email with 3-layer encryption
   - Create SHA-256 hash for lookup
   - Encrypt keys with master key
3. **Full name encryption** (if provided):
   - Encrypt with same keys
4. **Password hashing:**
   - Hash with bcrypt (not encrypted, already secure)
5. **Store in database:**
   - `encrypted_email`: Encrypted email bytes
   - `email_hash`: SHA-256 hash for lookup
   - `hashed_password`: Bcrypt hash
   - `encrypted_full_name`: Encrypted full name bytes
   - `encryption_metadata`: JSON with encrypted keys

### Login Flow

1. User submits email and password
2. **Lookup user:**
   - Hash email to get `email_hash`
   - Query database by `email_hash`
3. **Decrypt email:**
   - Decrypt keys from `encryption_metadata` using master key
   - Decrypt email using user keys
   - Verify decrypted email matches submitted email
4. **Verify password:**
   - Compare submitted password with `hashed_password` using bcrypt
5. **Return user data:**
   - Decrypt full_name if needed
   - Return user information

## 🛠️ Implementation Details

### Files Modified

1. **`app/models/user.py`**
   - User model with encrypted fields
   - Uses `BYTEA` for encrypted data storage

2. **`app/core/user_encryption.py`**
   - `encrypt_user_data()`: Encrypts user data
   - `decrypt_user_data()`: Decrypts user data
   - `hash_email_for_lookup()`: Creates email hash

3. **`app/api/v1/endpoints/auth.py`**
   - Updated `create_user()`: Encrypts data before storage
   - Updated `get_user_by_email()`: Decrypts data after retrieval

## 🚀 Setup Instructions

### 1. Create Database Table

```bash
# SSH into server
ssh root@freedomos.vulcantech.co

# Navigate to backend
cd /root/graohen_os/backend/py-service

# Activate virtual environment
source venv/bin/activate

# Run migration script
python scripts/create_user_table.py
```

### 2. Verify Table Creation

```bash
# Connect to PostgreSQL
psql -U postgres -d flashdash_db

# Check table exists
\dt users

# Check table structure
\d users

# Exit
\q
```

### 3. Test Registration

```bash
# Test registration endpoint
curl -X POST "https://freedomos.vulcantech.co/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

### 4. Verify Encryption

```bash
# Connect to database
psql -U postgres -d flashdash_db

# Check encrypted data (should be binary)
SELECT id, email_hash, 
       length(encrypted_email) as email_size,
       length(encrypted_full_name) as name_size
FROM users LIMIT 1;

# Exit
\q
```

## 🔒 Security Considerations

### 1. Master Key Management

**Current:** Derived from `SECRET_KEY` in `.env`

**Production Recommendation:**
- Use a dedicated key management service (AWS KMS, HashiCorp Vault)
- Rotate master key periodically
- Store master key separately from application code

### 2. Key Rotation

To rotate encryption keys:

1. Decrypt all user data
2. Generate new master key
3. Re-encrypt all user data
4. Update `SECRET_KEY` in `.env`

**Note:** This requires downtime and should be done carefully.

### 3. Backup Security

- Database backups contain encrypted data
- Master key is NOT in backups
- Without master key, encrypted data cannot be decrypted
- Store backups and master key separately

### 4. Access Control

- Limit database access to application only
- Use strong database passwords
- Enable SSL/TLS for database connections
- Restrict network access to database

## 📋 Migration from In-Memory Storage

If you have existing users in the in-memory store (`_users_db`):

1. **Export existing users** (if any)
2. **Create database table** (run migration script)
3. **Re-register users** (they'll be stored encrypted)
4. **Verify data** (check database)

## ✅ Verification Checklist

- [ ] Database table created
- [ ] Registration encrypts email
- [ ] Registration encrypts full_name
- [ ] Login decrypts email correctly
- [ ] Email hash lookup works
- [ ] Password verification works
- [ ] No plaintext emails in database
- [ ] Encryption metadata stored correctly

## 🐛 Troubleshooting

### Error: "Table 'users' does not exist"

```bash
# Run migration script
cd /root/graohen_os/backend/py-service
source venv/bin/activate
python scripts/create_user_table.py
```

### Error: "Failed to decrypt user data"

- Check `SECRET_KEY` in `.env` matches original
- Verify encryption metadata format
- Check database encoding

### Error: "Email hash collision"

- Extremely rare (SHA-256 collision)
- Log the collision for investigation
- User lookup will fail (security feature)

## 📚 Related Documentation

- [API README](./API_README.md) - API documentation
- [Authentication Guide](./AUTHENTICATION_GUIDE.md) - Frontend integration
- [MongoDB Migration Guide](./MONGODB_MIGRATION_GUIDE.md) - MongoDB migration
- [VPS Deployment Guide](../VPS_BACKEND_DEPLOYMENT.md) - Server deployment

---

**Security Note:** All user data is encrypted at rest. Even if the database is compromised, attackers cannot decrypt user emails or names without the master encryption key (derived from `SECRET_KEY`).
