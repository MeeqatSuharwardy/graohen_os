# Deployment Guide: Database Encryption Update

This guide explains how to deploy the updated authentication system with encrypted database storage.

## 📋 Overview

The authentication system has been updated to:
- Store user data (email, full_name) encrypted in PostgreSQL
- Use multi-layer encryption for maximum security
- Maintain compatibility with existing APIs

## 🔄 Deployment Steps

### Step 1: Backup Current Data

```bash
# SSH into server
ssh root@freedomos.vulcantech.co

# Backup PostgreSQL database (if you have existing users)
cd /root/graohen_os/backend/py-service
source venv/bin/activate

# Export any existing user data (if stored elsewhere)
# Note: Current implementation uses in-memory storage, so no migration needed
```

### Step 2: Pull Latest Code

```bash
# On server
cd /root/graohen_os

# Pull latest changes
git pull

# Or if deploying manually:
# Upload updated files to server
```

### Step 3: Update Dependencies

```bash
cd /root/graohen_os/backend/py-service
source venv/bin/activate

# Install/update dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Create Database Table

```bash
# Make script executable
chmod +x scripts/create_user_table.py

# Run migration script
python scripts/create_user_table.py
```

**Expected output:**
```
✅ User table created successfully!
   Table: users
   Fields: id, encrypted_email, email_hash, hashed_password, encrypted_full_name, etc.
```

### Step 5: Verify Table Creation

```bash
# Connect to PostgreSQL
psql -U postgres -d flashdash_db

# Check table
\dt users

# Check structure
\d users

# Should show:
# - id (integer, primary key)
# - encrypted_email (bytea)
# - email_hash (varchar)
# - hashed_password (varchar)
# - encrypted_full_name (bytea)
# - encryption_metadata (text)
# - is_active (boolean)
# - is_verified (boolean)
# - created_at (timestamp)
# - updated_at (timestamp)

\q
```

### Step 6: Restart Backend Service

```bash
# Restart backend
sudo systemctl restart flashdash-backend

# Check status
sudo systemctl status flashdash-backend

# View logs
sudo journalctl -u flashdash-backend -f
```

### Step 7: Test Registration

```bash
# Test registration endpoint
curl -X POST "https://freedomos.vulcantech.co/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test_encrypted@fxmail.ai",
    "password": "TestPass123!",
    "full_name": "Test User Encrypted"
  }'

# Should return tokens if successful
```

### Step 8: Verify Encryption

```bash
# Connect to database
psql -U postgres -d flashdash_db

# Check encrypted data
SELECT 
    id,
    email_hash,
    length(encrypted_email) as email_size,
    length(encrypted_full_name) as name_size,
    length(encryption_metadata) as metadata_size
FROM users 
WHERE email_hash = (
    SELECT email_hash FROM users LIMIT 1
);

# encrypted_email and encrypted_full_name should be binary (bytea)
# encryption_metadata should be JSON text

\q
```

## ✅ Verification Checklist

- [ ] Code pulled/updated on server
- [ ] Dependencies installed
- [ ] Database table created
- [ ] Backend service restarted
- [ ] Registration endpoint works
- [ ] Login endpoint works
- [ ] Data is encrypted in database
- [ ] Email hash lookup works
- [ ] No errors in logs

## 🔒 Security Verification

### Check Encryption

```bash
# Connect to database
psql -U postgres -d flashdash_db

# Verify no plaintext emails
SELECT encrypted_email FROM users LIMIT 1;
# Should show: \\x... (binary data, not readable text)

# Verify email hash is present
SELECT email_hash FROM users LIMIT 1;
# Should show: 64-character hex string

\q
```

### Test Decryption

```bash
# Test login (this decrypts email)
curl -X POST "https://freedomos.vulcantech.co/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test_encrypted@fxmail.ai",
    "password": "TestPass123!"
  }'

# Should return tokens if decryption works
```

## 🐛 Troubleshooting

### Error: "Table 'users' does not exist"

**Solution:**
```bash
cd /root/graohen_os/backend/py-service
source venv/bin/activate
python scripts/create_user_table.py
```

### Error: "Failed to decrypt user data"

**Possible causes:**
1. `SECRET_KEY` changed - encryption keys derived from SECRET_KEY
2. Corrupted encryption metadata
3. Database encoding issues

**Solution:**
- Verify `SECRET_KEY` in `.env` matches original
- Check encryption_metadata format in database
- Re-register users if needed

### Error: "Email hash collision"

**Note:** Extremely rare (SHA-256 collision probability is negligible)

**If it occurs:**
- Log the collision for investigation
- User lookup will fail (security feature)
- Consider using longer hash or additional verification

### Backend Not Starting

**Check logs:**
```bash
sudo journalctl -u flashdash-backend -n 50
```

**Common issues:**
- Missing dependencies: `pip install -r requirements.txt`
- Database connection error: Check `.env` DATABASE_URL
- Import errors: Verify all files are uploaded

## 📝 Post-Deployment

### 1. Monitor Logs

```bash
# Watch logs for errors
sudo journalctl -u flashdash-backend -f
```

### 2. Test All Endpoints

- Registration
- Login
- Email APIs
- Drive APIs

### 3. Verify Data Integrity

- Check encrypted data in database
- Test user lookup
- Verify password verification

## 🔄 Rollback Plan

If issues occur:

1. **Stop backend:**
   ```bash
   sudo systemctl stop flashdash-backend
   ```

2. **Revert code:**
   ```bash
   cd /root/graohen_os
   git checkout <previous-commit>
   ```

3. **Restart backend:**
   ```bash
   sudo systemctl start flashdash-backend
   ```

**Note:** Users registered with encryption cannot be accessed after rollback unless you migrate their data.

## 📚 Related Documentation

- [Database Encryption Guide](./DATABASE_ENCRYPTION_GUIDE.md) - Detailed encryption explanation
- [MongoDB Migration Guide](./MONGODB_MIGRATION_GUIDE.md) - MongoDB migration steps
- [VPS Deployment Guide](../VPS_BACKEND_DEPLOYMENT.md) - Server setup
- [API README](./API_README.md) - API documentation

---

**Important:** After deployment, all new user registrations will store encrypted data. Existing in-memory users (if any) will need to re-register.
