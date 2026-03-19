"""APK Management Routes - Upload, list, and install APKs on devices"""

from fastapi import APIRouter, HTTPException, Depends, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
import secrets
import logging
from pathlib import Path
from ..config import settings
from ..utils.tools import run_adb_command

router = APIRouter()
logger = logging.getLogger(__name__)

# Password for APK upload form
APK_UPLOAD_PASSWORD = "AllHailToEagle"

# Directory to store uploaded APKs - uses APK_STORAGE_DIR from .env or defaults to ~/.graphene-installer/apks
APK_STORAGE_DIR_STR = settings.APK_STORAGE_DIR
# Expand user home directory (~) if present
APK_STORAGE_DIR_STR = os.path.expanduser(APK_STORAGE_DIR_STR)
APK_STORAGE_DIR = Path(APK_STORAGE_DIR_STR)

# Ensure APK storage directory exists
try:
    APK_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError) as e:
    logger.warning(f"Could not create APK storage directory at {APK_STORAGE_DIR}: {e}")
    # Fallback to a local directory in the project
    APK_STORAGE_DIR = Path(__file__).parent.parent.parent / "apks"
    try:
        APK_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using fallback APK storage directory: {APK_STORAGE_DIR}")
    except (OSError, PermissionError) as fallback_error:
        logger.error(f"Failed to create fallback APK storage directory: {fallback_error}")
        raise

logger.info(f"APK storage directory: {APK_STORAGE_DIR}")


class DeviceDetectionRequest(BaseModel):
    """Request model for device detection from electron app"""
    serial: str
    state: str  # 'device', 'fastboot', 'unauthorized', 'offline'
    codename: Optional[str] = None
    device_name: Optional[str] = None


class APKInfo(BaseModel):
    """APK information model"""
    filename: str
    size: int
    upload_time: str


class InstallAPKRequest(BaseModel):
    """Request model for installing APK"""
    device_serial: str
    apk_filename: str


def verify_password(credentials: HTTPBasicCredentials):
    """Verify password for APK upload form"""
    password = credentials.password
    if password != APK_UPLOAD_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Invalid password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@router.post("/devices/detect", response_model=dict)
async def detect_device(request: DeviceDetectionRequest):
    """API endpoint for electron app to send detected device information"""
    try:
        logger.info(f"Device detection received: {request.serial} in state {request.state}")
        
        # Store device info (could be stored in Redis or database)
        # For now, just log and return success
        device_info = {
            "serial": request.serial,
            "state": request.state,
            "codename": request.codename,
            "device_name": request.device_name,
        }
        
        logger.info(f"Device info stored: {device_info}")
        
        return {
            "success": True,
            "message": "Device detection received",
            "device": device_info,
        }
    except Exception as e:
        logger.error(f"Error in device detection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload", response_class=HTMLResponse)
async def get_upload_form(
    credentials: HTTPBasicCredentials = Depends(HTTPBasic(auto_error=False)),
):
    """Password-protected HTML form for APK upload"""
    # Check if password is provided
    if not credentials or credentials.password != APK_UPLOAD_PASSWORD:
        # Return login form
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>APK Upload - Authentication Required</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }}
                    .container {{
                        background: white;
                        padding: 2rem;
                        border-radius: 10px;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                        max-width: 400px;
                        width: 100%;
                    }}
                    h1 {{
                        margin-top: 0;
                        color: #333;
                    }}
                    form {{
                        display: flex;
                        flex-direction: column;
                        gap: 1rem;
                    }}
                    input {{
                        padding: 0.75rem;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        font-size: 1rem;
                    }}
                    button {{
                        padding: 0.75rem;
                        background: #667eea;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 1rem;
                        cursor: pointer;
                    }}
                    button:hover {{
                        background: #5568d3;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>APK Upload Portal</h1>
                    <p>Please enter the password to access the upload form:</p>
                    <form method="get" action="/apks/upload">
                        <input type="text" name="username" placeholder="Username" value="admin" required>
                        <input type="password" name="password" placeholder="Password" required>
                        <button type="submit">Authenticate</button>
                    </form>
                </div>
            </body>
            </html>
            """,
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Return upload form
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>APK Upload Form</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 2rem;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 2rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    margin-top: 0;
                    color: #333;
                }}
                form {{
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                }}
                input[type="file"] {{
                    padding: 0.5rem;
                    border: 2px dashed #ddd;
                    border-radius: 5px;
                    cursor: pointer;
                }}
                button {{
                    padding: 0.75rem 1.5rem;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 1rem;
                    cursor: pointer;
                }}
                button:hover {{
                    background: #5568d3;
                }}
                .message {{
                    padding: 1rem;
                    border-radius: 5px;
                    margin: 1rem 0;
                }}
                .success {{
                    background: #d4edda;
                    color: #155724;
                    border: 1px solid #c3e6cb;
                }}
                .error {{
                    background: #f8d7da;
                    color: #721c24;
                    border: 1px solid #f5c6cb;
                }}
                .apk-list {{
                    margin-top: 2rem;
                    padding-top: 2rem;
                    border-top: 1px solid #ddd;
                }}
                .apk-item {{
                    padding: 1rem;
                    background: #f8f9fa;
                    border-radius: 5px;
                    margin: 0.5rem 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>APK Upload Form</h1>
                <form method="post" action="/apks/upload" enctype="multipart/form-data">
                    <label for="file">Select APK file:</label>
                    <input type="file" name="file" id="file" accept=".apk" required>
                    <input type="hidden" name="username" value="{credentials.username}">
                    <input type="hidden" name="password" value="{credentials.password}">
                    <button type="submit">Upload APK</button>
                </form>
                <div class="apk-list">
                    <h2>Uploaded APKs</h2>
                    <div id="apk-list"></div>
                </div>
            </div>
            <script>
                // Load APK list
                fetch('/apks/list')
                    .then(r => r.json())
                    .then(data => {{
                        const listDiv = document.getElementById('apk-list');
                        if (data.length === 0) {{
                            listDiv.innerHTML = '<p>No APKs uploaded yet.</p>';
                        }} else {{
                            listDiv.innerHTML = data.map(apk => `
                                <div class="apk-item">
                                    <span>${{apk.filename}} (${{(apk.size / 1024 / 1024).toFixed(2)}} MB)</span>
                                    <span>${{apk.upload_time}}</span>
                                </div>
                            `).join('');
                        }}
                    }});
            </script>
        </body>
        </html>
        """
    )


@router.post("/upload")
async def upload_apk(
    file: UploadFile = File(...),
    username: str = Form(...),
    password: str = Form(...),
):
    """Upload APK file"""
    # Verify password
    if password != APK_UPLOAD_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Check file extension
    if not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="File must be an APK file (.apk)")
    
    try:
        # Save file
        file_path = APK_STORAGE_DIR / file.filename
        
        # Handle duplicate filenames
        counter = 1
        original_path = file_path
        while file_path.exists():
            stem = original_path.stem
            suffix = original_path.suffix
            file_path = APK_STORAGE_DIR / f"{stem}_{counter}{suffix}"
            counter += 1
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"APK uploaded: {file_path} ({len(content)} bytes)")
        
        # Return success with redirect to form
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Upload Successful</title>
                <meta http-equiv="refresh" content="3;url=/apks/upload?username={username}&password={password}">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: #f5f5f5;
                    }}
                    .container {{
                        background: white;
                        padding: 2rem;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        text-align: center;
                    }}
                    .success {{
                        color: #155724;
                        background: #d4edda;
                        padding: 1rem;
                        border-radius: 5px;
                        margin: 1rem 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success">
                        <h2>✓ APK uploaded successfully!</h2>
                        <p>File: {file_path.name}</p>
                        <p>Size: {(len(content) / 1024 / 1024):.2f} MB</p>
                        <p>Redirecting back to upload form...</p>
                    </div>
                </div>
            </body>
            </html>
            """
        )
    except Exception as e:
        logger.error(f"Error uploading APK: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload APK: {str(e)}")


@router.get("/list", response_model=List[APKInfo])
async def list_apks():
    """List all uploaded APKs"""
    try:
        apks = []
        for apk_file in APK_STORAGE_DIR.glob("*.apk"):
            stat = apk_file.stat()
            apks.append({
                "filename": apk_file.name,
                "size": stat.st_size,
                "upload_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        
        # Sort by upload time (newest first)
        apks.sort(key=lambda x: x["upload_time"], reverse=True)
        return apks
    except Exception as e:
        logger.error(f"Error listing APKs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install")
async def install_apk(request: InstallAPKRequest):
    """Install APK on connected device via ADB"""
    try:
        apk_path = APK_STORAGE_DIR / request.apk_filename
        
        if not apk_path.exists():
            raise HTTPException(status_code=404, detail=f"APK not found: {request.apk_filename}")
        
        logger.info(f"Installing APK {request.apk_filename} on device {request.device_serial}")
        
        # Run adb install command
        result = run_adb_command(
            ["install", "-r", str(apk_path)],
            serial=request.device_serial,
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to execute ADB install command")
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout or "Unknown error"
            raise HTTPException(
                status_code=500,
                detail=f"Failed to install APK: {error_msg}"
            )
        
        logger.info(f"APK installed successfully on {request.device_serial}")
        
        return {
            "success": True,
            "message": f"APK {request.apk_filename} installed successfully",
            "device_serial": request.device_serial,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing APK: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

