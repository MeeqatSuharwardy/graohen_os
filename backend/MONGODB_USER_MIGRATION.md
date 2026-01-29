# MongoDB User Migration Guide

This guide explains how to migrate user storage from PostgreSQL to MongoDB.

## 📋 Overview

The authentication system has been updated to use MongoDB for user storage instead of PostgreSQL. All user data (email, full_name) is encrypted with multi-layer encryption and stored in MongoDB.

## 🔄 Changes Made

### 1. New MongoDB User Service
- **File**: `backend/py-service/app/services/user_service_mongodb.py`
- Provides MongoDB-based user storage with encryption
- Similar to `email_service_mongodb.py` and `drive_service_mongodb.py`

### 2. Updated Authentication Endpoints
- **File**: `backend/py-service/app/api/v1/endpoints/auth.py`
- Removed PostgreSQL dependencies (`AsyncSession`, `get_db`, `User` model)
- Now uses `get_user_service()` from MongoDB service
- All endpoints updated: `register`, `login`, `get_current_user`

### 3. MongoDB Configuration
- **File**: `backend/py-service/app/config.py`
- MongoDB connection string already configured:
  ```
  mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin
  ```
- Database: `admin`

## 🚀 Deployment Steps

### Step 1: Deploy Updated Code

```bash
# SSH into server
ssh root@freedomos.vulcantech.co

# Navigate to project directory
cd /root/graohen_os

# Pull latest changes (or upload files)
git pull
# OR upload the updated files manually

# Navigate to backend
cd backend/py-service
source venv/bin/activate

# Install/update dependencies (if needed)
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Setup MongoDB Users Collection

```bash
# Run setup script to create indexes
python3 scripts/setup_mongodb_users.py
```

**Expected output:**
```
✅ Created index: email_hash (unique, sparse)
✅ Created index: created_at
✅ Created index: is_active
✅ Created compound index: is_active + created_at
✅ Users collection setup complete!
```

### Step 3: Restart Backend Service

```bash
# Restart backend
sudo systemctl restart flashdash-backend

# Check status
sudo systemctl status flashdash-backend

# View logs
sudo journalctl -u flashdash-backend -f
```

### Step 4: Register Test Accounts

```bash
# Run registration script
python3 scripts/create_and_register_users_mongodb.py
```

**Or register manually via API:**
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test20@fxmail.ai",
    "password": "test20@#",
    "full_name": "Test User 20"
  }'
```

## 📊 MongoDB Users Collection Structure

### Document Schema
```json
{
  "_id": ObjectId("..."),
  "encrypted_email": Binary("..."),  // Encrypted email bytes
  "email_hash": "sha256_hash...",     // SHA-256 hash for lookup
  "hashed_password": "bcrypt_hash...", // Bcrypt hashed password
  "encrypted_full_name": Binary("..."), // Encrypted full name bytes (optional)
  "encryption_metadata": "{...}",     // JSON metadata for decryption
  "is_active": true,
  "is_verified": false,
  "created_at": ISODate("..."),
  "updated_at": ISODate("...")
}
```

### Indexes
- `email_hash_unique`: Unique sparse index on `email_hash` (for fast lookups)
- `created_at_idx`: Index on `created_at` (for sorting)
- `is_active_idx`: Index on `is_active` (for filtering)
- `active_created_idx`: Compound index on `is_active` + `created_at`

## 🔒 Encryption Details

- **Email**: Encrypted with multi-layer encryption (AES-256-GCM, ChaCha20-Poly1305, AES-256-GCM with Scrypt)
- **Full Name**: Encrypted with same keys as email
- **Email Hash**: SHA-256 hash for fast lookups (not encrypted, but one-way)
- **Password**: Bcrypt hashed (one-way)

## ✅ Verification

### Check Users Collection
```bash
# Connect to MongoDB (if you have mongosh installed)
mongosh "mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin"

# Switch to admin database
use admin

# Count users
db.users.countDocuments()

# List users (shows encrypted data)
db.users.find().pretty()

# Check indexes
db.users.getIndexes()
```

### Test Registration API
```bash
# Test registration
curl -X POST "https://freedomos.vulcantech.co/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test20@fxmail.ai",
    "password": "test20@#",
    "full_name": "Test User 20"
  }'

# Test login
curl -X POST "https://freedomos.vulcantech.co/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test20@fxmail.ai",
    "password": "test20@#"
  }'
```

## 🐛 Troubleshooting

### Error: "Failed to create user account" (500)

**Possible causes:**
1. MongoDB not initialized in FastAPI app
2. MongoDB connection string incorrect
3. Collection not set up (missing indexes)

**Solution:**
```bash
# Check MongoDB connection
python3 -c "
from app.core.mongodb import init_mongodb, get_mongodb
import asyncio
asyncio.run(init_mongodb())
db = get_mongodb()
print('MongoDB connected:', db.name)
"

# Setup collection
python3 scripts/setup_mongodb_users.py

# Check backend logs
sudo journalctl -u flashdash-backend -n 50
```

### Error: "Email already registered" (400)

**Solution:** User already exists. Try login instead:
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test20@fxmail.ai", "password": "test20@#"}'
```

### Error: "MongoDB not initialized"

**Solution:** Ensure MongoDB is initialized in `app/main.py`:
```python
if HAS_MONGODB:
    try:
        await init_mongodb()
        logger.info("MongoDB initialized")
    except Exception as e:
        logger.warning(f"MongoDB initialization failed: {e}")
```

## 📝 Test Accounts

After deployment, register these test accounts:

1. **Email**: test20@fxmail.ai  
   **Password**: test20@#

2. **Email**: test21@fxmail.ai  
   **Password**: test20@#

## 🔄 Migration Notes

- **No data migration needed**: This is a fresh implementation
- **PostgreSQL users table**: Can be ignored/removed (not used anymore)
- **All new users**: Will be stored in MongoDB with encryption
- **Existing users**: Need to re-register (if any existed)

## 📚 Related Files

- `backend/py-service/app/services/user_service_mongodb.py` - MongoDB user service
- `backend/py-service/app/api/v1/endpoints/auth.py` - Updated auth endpoints
- `backend/py-service/scripts/setup_mongodb_users.py` - Collection setup script
- `backend/py-service/scripts/create_and_register_users_mongodb.py` - Registration script
- `backend/py-service/app/core/user_encryption.py` - Encryption utilities

---

**Important:** After deployment, all user registrations will be stored in MongoDB with multi-layer encryption. The system now uses MongoDB for everything: users, emails, and files.
