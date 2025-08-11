# Simple OTP Service without complex dependencies
# This version should deploy reliably on Render.com

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import hmac
import hashlib
import struct
import time
import base64
import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
import json

# Simple configuration
API_KEY = os.getenv("API_KEY", "UkFPS1EXdV8SmopIby5TvY2kCTsu228c")
MASTER_SECRET = os.getenv("MASTER_SECRET", "cxxH4qNRyLeePT49yRJev1kRdF1Cu0jA1e8FA2sGQZw")
PORT = int(os.getenv("PORT", "10000"))

app = FastAPI(title="Simple OTP Service", version="1.0.0")
security = HTTPBearer()

# Simple in-memory storage for demo (use database in production)
devices_db = {}
audit_logs = []

# Pydantic models
class DeviceRegistration(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=100)

class OTPVerification(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    otp: int = Field(..., ge=0, le=999999)

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# Simple OTP Service
class SimpleOTPService:
    def __init__(self, master_secret: str):
        self.master_secret = master_secret.encode()
    
    def generate_derived_key(self, device_id: str) -> bytes:
        return hmac.new(self.master_secret, device_id.encode(), hashlib.sha256).digest()
    
    def generate_otp(self, secret_key: bytes, digits: int = 6, interval: int = 30) -> int:
        time_step = int(time.time() // interval)
        msg = struct.pack(">Q", time_step)
        hmac_hash = hmac.new(secret_key, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        truncated_hash = hmac_hash[offset:offset + 4]
        code_int = struct.unpack(">I", truncated_hash)[0] & 0x7FFFFFFF
        return code_int % (10 ** digits)
    
    def verify_otp(self, device_id: str, otp: int, window: int = 1) -> bool:
        derived_key = self.generate_derived_key(device_id)
        current_time_step = int(time.time() // 30)
        
        for offset in range(-window, window + 1):
            time_step = current_time_step + offset
            if self.generate_otp_at_time(derived_key, time_step) == otp:
                return True
        return False
    
    def generate_otp_at_time(self, secret_key: bytes, time_step: int) -> int:
        msg = struct.pack(">Q", time_step)
        hmac_hash = hmac.new(secret_key, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        truncated_hash = hmac_hash[offset:offset + 4]
        code_int = struct.unpack(">I", truncated_hash)[0] & 0x7FFFFFFF
        return code_int % (10 ** 6)

otp_service = SimpleOTPService(MASTER_SECRET)

# Authentication
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials

# Routes
@app.get("/")
async def root():
    return {"service": "Simple OTP Service", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "database": "memory"
    }

@app.post("/api/v1/devices/register", response_model=APIResponse)
async def register_device(
    device_data: DeviceRegistration,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Register a new device"""
    try:
        if device_data.device_id in devices_db:
            raise HTTPException(status_code=400, detail="Device already registered")
        
        derived_key = otp_service.generate_derived_key(device_data.device_id)
        derived_key_b64 = base64.b64encode(derived_key).decode()
        
        devices_db[device_data.device_id] = {
            "user_id": device_data.user_id,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True
        }
        
        audit_logs.append({
            "device_id": device_data.device_id,
            "action": "DEVICE_REGISTERED",
            "success": True,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return APIResponse(
            success=True,
            message="Device registered successfully",
            data={
                "device_id": device_data.device_id,
                "derived_key": derived_key_b64
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/v1/otp/verify", response_model=APIResponse)
async def verify_otp(
    otp_data: OTPVerification,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Verify an OTP"""
    try:
        if otp_data.device_id not in devices_db:
            raise HTTPException(status_code=400, detail="Device not found")
        
        device = devices_db[otp_data.device_id]
        if not device["is_active"]:
            raise HTTPException(status_code=400, detail="Device is inactive")
        
        is_valid = otp_service.verify_otp(otp_data.device_id, otp_data.otp)
        
        audit_logs.append({
            "device_id": otp_data.device_id,
            "action": "OTP_VERIFICATION",
            "success": is_valid,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": request.client.host if request.client else "unknown"
        })
        
        return APIResponse(
            success=True,
            message="OTP verification completed",
            data={"valid": is_valid}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Verification failed")

@app.post("/api/v1/devices/{device_id}/deactivate", response_model=APIResponse)
async def deactivate_device(
    device_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Deactivate a device"""
    try:
        if device_id not in devices_db:
            raise HTTPException(status_code=400, detail="Device not found")
        
        devices_db[device_id]["is_active"] = False
        devices_db[device_id]["deactivated_at"] = datetime.utcnow().isoformat()
        
        audit_logs.append({
            "device_id": device_id,
            "action": "DEVICE_DEACTIVATED",
            "success": True,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return APIResponse(
            success=True,
            message="Device deactivated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Deactivation failed")

# Debug endpoint for testing
@app.get("/api/v1/debug/devices")
async def list_devices(credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)):
    """List all devices (debug only)"""
    return {"devices": devices_db, "audit_logs": audit_logs[-10:]}  # Last 10 logs

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
