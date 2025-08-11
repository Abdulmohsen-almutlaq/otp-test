from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import structlog
import time
from datetime import datetime

from .config import settings
from .database import get_db, create_tables, check_db_health
from .otp_service import EnterpriseOTPService, ClientOTP

# Initialize logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize FastAPI app
app = FastAPI(
    title="Enterprise OTP Service",
    description="Production-ready TOTP authentication service",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
otp_service = EnterpriseOTPService()

# Pydantic models
class DeviceRegistration(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=100)

class OTPVerification(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    otp: int = Field(..., ge=0, le=999999)

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    database: str

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# Authentication middleware
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not settings.api_key or credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return credentials

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and perform startup checks"""
    logger.info("Starting OTP Service", version="1.0.0", environment=settings.environment)
    create_tables()
    
    if not check_db_health():
        logger.error("Database health check failed")
        raise Exception("Database connection failed")
    
    logger.info("OTP Service started successfully")

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring"""
    db_status = "healthy" if check_db_health() else "unhealthy"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "unhealthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        database=db_status
    )

# Device registration endpoint
@app.post("/api/v1/devices/register", response_model=APIResponse)
async def register_device(
    request: Request,
    device_data: DeviceRegistration,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Register a new device for OTP generation"""
    start_time = time.time()
    
    try:
        result = otp_service.register_device(
            device_id=device_data.device_id,
            user_id=device_data.user_id,
            db=db
        )
        
        if "error" in result:
            logger.warning("Device registration failed", 
                         device_id=device_data.device_id,
                         error=result["error"])
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Don't include derived_key in logs
        logger.info("Device registered successfully",
                   device_id=device_data.device_id,
                   user_id=device_data.user_id,
                   duration=time.time() - start_time)
        
        return APIResponse(
            success=True,
            message="Device registered successfully",
            data={
                "device_id": result["device_id"],
                "derived_key": result["derived_key"]  # Only return in API response
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Device registration error",
                    device_id=device_data.device_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# OTP verification endpoint
@app.post("/api/v1/otp/verify", response_model=APIResponse)
async def verify_otp(
    request: Request,
    otp_data: OTPVerification,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Verify an OTP for a registered device"""
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        result = otp_service.verify_otp(
            device_id=otp_data.device_id,
            otp=otp_data.otp,
            db=db,
            ip_address=client_ip
        )
        
        if "error" in result:
            logger.warning("OTP verification failed",
                         device_id=otp_data.device_id,
                         error=result["error"],
                         ip_address=client_ip)
            raise HTTPException(status_code=400, detail=result["error"])
        
        logger.info("OTP verification completed",
                   device_id=otp_data.device_id,
                   valid=result["valid"],
                   ip_address=client_ip,
                   duration=time.time() - start_time)
        
        return APIResponse(
            success=True,
            message="OTP verification completed",
            data={"valid": result["valid"]}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("OTP verification error",
                    device_id=otp_data.device_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# Device deactivation endpoint
@app.post("/api/v1/devices/{device_id}/deactivate", response_model=APIResponse)
async def deactivate_device(
    device_id: str,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(verify_api_key)
):
    """Deactivate a device"""
    try:
        result = otp_service.deactivate_device(device_id=device_id, db=db)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return APIResponse(
            success=True,
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Device deactivation error",
                    device_id=device_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# Test endpoint (only in debug mode)
@app.post("/api/v1/test/generate-otp")
async def test_generate_otp(derived_key_b64: str):
    """Test endpoint to generate OTP from derived key (debug only)"""
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    
    try:
        client = ClientOTP(derived_key_b64)
        otp = client.generate_otp()
        
        return {
            "otp": otp,
            "message": "OTP generated for testing"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "Enterprise OTP Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
