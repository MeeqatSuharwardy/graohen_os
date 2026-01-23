# 📤 Upload Instructions - Shared Hosting

## ✅ Builds Complete!

All files have been built and are ready in: **`shared-hosting-upload/`**

## 📍 Location of Built Files

**Directory**: `/Users/vt_dev/upwork_graphene/graohen_os/shared-hosting-upload/`

### Contents:

```
shared-hosting-upload/
├── index.html              # Main frontend file
├── assets/                 # JS, CSS, images (all frontend assets)
│   ├── index-*.js
│   ├── index-*.css
│   └── *.png, *.svg, etc.
├── downloads/              # Desktop app installers
│   ├── FlashDash-Setup-1.0.0.exe    # Windows (if built)
│   ├── FlashDash-1.0.0.dmg           # Mac (if built)
│   └── flashdash-1.0.0.AppImage     # Linux (if built)
└── .htaccess               # Apache configuration
```

## 🚀 How to Upload

### Method 1: FTP Client (Recommended)

**Using FileZilla, WinSCP, or similar:**

1. **Open your FTP client**
2. **Connect to your shared hosting:**
   - **Host**: `your-domain.com` or FTP IP address
   - **Username**: Your FTP username
   - **Password**: Your FTP password
   - **Port**: `21` (FTP) or `22` (SFTP)

3. **Navigate to public directory:**
   - Usually: `/public_html/` or `/www/` or `/htdocs/`
   - This is your website's root directory

4. **Upload all files:**
   - Select **ALL files** from `shared-hosting-upload/` folder
   - Drag and drop to `public_html/`
   - Make sure to upload:
     - `index.html`
     - `assets/` folder (with all contents)
     - `downloads/` folder (with all desktop apps)
     - `.htaccess` file

5. **Set file permissions:**
   - **Files**: `644` (rw-r--r--)
   - **Directories**: `755` (rwxr-xr-x)
   - Right-click files → Properties → Permissions

### Method 2: cPanel File Manager

1. **Login to cPanel**
2. **Click "File Manager"**
3. **Navigate to `public_html`**
4. **Click "Upload" button**
5. **Select all files** from `shared-hosting-upload/`:
   - `index.html`
   - `assets/` folder
   - `downloads/` folder
   - `.htaccess`
6. **Upload files**
7. **Set permissions** (if needed):
   - Select files → Right-click → Change Permissions
   - Files: `644`, Directories: `755`

### Method 3: Command Line (SSH)

If you have SSH access:

```bash
# On your local machine
cd /Users/vt_dev/upwork_graphene/graohen_os/shared-hosting-upload

# Upload via SCP
scp -r * user@your-domain.com:/home/user/public_html/

# Or use rsync
rsync -avz . user@your-domain.com:/home/user/public_html/
```

## ✅ Verification Checklist

After uploading, verify:

- [ ] `index.html` is in `public_html/`
- [ ] `assets/` folder exists with files
- [ ] `downloads/` folder exists with desktop apps
- [ ] `.htaccess` file is uploaded
- [ ] File permissions are correct (644/755)

## 🧪 Test Your Deployment

### 1. Test Frontend
Visit: `https://your-domain.com`
- Should see FlashDash interface
- Check browser console (F12) - should connect to `https://freedomos.vulcantech.co`

### 2. Test Downloads
- **Windows**: `https://your-domain.com/downloads/FlashDash-Setup-1.0.0.exe`
- **Mac**: `https://your-domain.com/downloads/FlashDash-1.0.0.dmg`
- **Linux**: `https://your-domain.com/downloads/flashdash-1.0.0.AppImage`

All should download properly.

## 🔧 Configuration

**Backend API**: `https://freedomos.vulcantech.co` ✅ (Already configured in builds)

**Download URLs**: Will automatically use your shared hosting domain

## 📝 Important Notes

- **No code changes needed** - Backend URL is already set to `https://freedomos.vulcantech.co`
- **All builds done** - You just upload files
- **Desktop apps included** - Windows EXE, Mac DMG, Linux AppImage (if built on your system)
- **.htaccess included** - Apache configuration for SPA routing and downloads

## 🆘 Troubleshooting

### Frontend Not Loading
- Check file permissions (should be 644)
- Verify `index.html` is in root directory
- Check `.htaccess` is uploaded

### Downloads Not Working
- Verify `downloads/` folder exists
- Check file permissions on download files
- Test direct URL: `https://your-domain.com/downloads/FlashDash-Setup-1.0.0.exe`

### API Not Connecting
- Check browser console for errors
- Verify backend is live: `https://freedomos.vulcantech.co/health`
- Check CORS settings on backend

---

**Everything is ready!** Upload the `shared-hosting-upload/` folder contents to your shared hosting and you're live! 🎉
