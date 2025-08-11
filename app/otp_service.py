import hmac
import hashlib
import struct
import time
import secrets
import base64
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .database import get_db, Device, AuditLog
from .config import settings
import structlog

logger = structlog.get_logger()

class EnterpriseOTPService:
    def __init__(self):
        if not settings.master_secret:
            raise ValueError("MASTER_SECRET environment variable is required")
        self.master_secret = settings.master_secret.encode()

    def generate_derived_key(self, device_id: str) -> bytes:
        """Generate derived key unique to device"""
        return hmac.new(
            self.master_secret, 
            device_id.encode(), 
            hashlib.sha256
        ).digest()

    def register_device(self, device_id: str, user_id: str, db: Session) -> dict:
        """Register a new device and return derived key"""
        try:
            # Check if device already exists
            existing_device = db.query(Device).filter(Device.device_id == device_id).first()
            if existing_device:
                logger.warning("Device already registered", device_id=device_id)
                return {"error": "Device already registered"}

            # Generate derived key
            derived_key = self.generate_derived_key(device_id)
            derived_key_b64 = base64.b64encode(derived_key).decode()

            # Store device in database
            device = Device(
                device_id=device_id,
                user_id=user_id,
                derived_key_hash=hashlib.sha256(derived_key).hexdigest(),
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(device)
            
            # Log registration
            audit_log = AuditLog(
                device_id=device_id,
                action="DEVICE_REGISTERED",
                success=True,
                timestamp=datetime.utcnow(),
                ip_address="unknown"
            )
            db.add(audit_log)
            db.commit()

            logger.info("Device registered successfully", device_id=device_id, user_id=user_id)
            
            return {
                "derived_key": derived_key_b64,
                "device_id": device_id,
                "message": "Device registered successfully"
            }

        except Exception as e:
            db.rollback()
            logger.error("Failed to register device", device_id=device_id, error=str(e))
            return {"error": "Registration failed"}

    def verify_otp(self, device_id: str, otp: int, db: Session, ip_address: str = "unknown") -> dict:
        """Verify OTP with enhanced security and logging"""
        try:
            # Check if device exists and is active
            device = db.query(Device).filter(
                Device.device_id == device_id,
                Device.is_active == True
            ).first()
            
            if not device:
                self._log_verification(db, device_id, "INVALID_DEVICE", False, ip_address)
                return {"valid": False, "error": "Device not found or inactive"}

            # Check rate limiting (basic implementation)
            recent_attempts = db.query(AuditLog).filter(
                AuditLog.device_id == device_id,
                AuditLog.action == "OTP_VERIFICATION",
                AuditLog.timestamp > datetime.utcnow() - timedelta(minutes=5)
            ).count()

            if recent_attempts > 10:
                self._log_verification(db, device_id, "RATE_LIMITED", False, ip_address)
                return {"valid": False, "error": "Rate limit exceeded"}

            # Generate derived key and verify OTP
            derived_key = self.generate_derived_key(device_id)
            is_valid = self._verify_totp(derived_key, otp)

            # Update device last used
            if is_valid:
                device.last_used = datetime.utcnow()
                device.usage_count += 1

            # Log verification attempt
            self._log_verification(db, device_id, "OTP_VERIFICATION", is_valid, ip_address)
            db.commit()

            logger.info("OTP verification completed", 
                       device_id=device_id, 
                       valid=is_valid, 
                       ip_address=ip_address)

            return {"valid": is_valid}

        except Exception as e:
            db.rollback()
            logger.error("OTP verification failed", device_id=device_id, error=str(e))
            return {"valid": False, "error": "Verification failed"}

    def _verify_totp(self, secret_key: bytes, otp: int) -> bool:
        """Time-based OTP verification with window tolerance"""
        current_time_step = int(time.time() // settings.otp_interval)
        
        # Check OTP in time window +/- window to allow clock drift
        for offset in range(-settings.otp_window, settings.otp_window + 1):
            time_step = current_time_step + offset
            if self._generate_otp(secret_key, time_step) == otp:
                return True
        return False

    def _generate_otp(self, secret_key: bytes, time_step: int) -> int:
        """Generate TOTP using HMAC-SHA1"""
        # Pack time step into bytes
        msg = struct.pack(">Q", time_step)
        # HMAC-SHA1 with derived key
        hmac_hash = hmac.new(secret_key, msg, hashlib.sha1).digest()
        # Dynamic truncation
        offset = hmac_hash[-1] & 0x0F
        truncated_hash = hmac_hash[offset:offset + 4]
        code_int = struct.unpack(">I", truncated_hash)[0] & 0x7FFFFFFF
        # Return code modulo digits
        return code_int % (10 ** settings.otp_digits)

    def _log_verification(self, db: Session, device_id: str, action: str, success: bool, ip_address: str):
        """Log verification attempt"""
        audit_log = AuditLog(
            device_id=device_id,
            action=action,
            success=success,
            timestamp=datetime.utcnow(),
            ip_address=ip_address
        )
        db.add(audit_log)

    def deactivate_device(self, device_id: str, db: Session) -> dict:
        """Deactivate a device"""
        try:
            device = db.query(Device).filter(Device.device_id == device_id).first()
            if not device:
                return {"error": "Device not found"}

            device.is_active = False
            device.deactivated_at = datetime.utcnow()
            
            # Log deactivation
            audit_log = AuditLog(
                device_id=device_id,
                action="DEVICE_DEACTIVATED",
                success=True,
                timestamp=datetime.utcnow(),
                ip_address="system"
            )
            db.add(audit_log)
            db.commit()

            logger.info("Device deactivated", device_id=device_id)
            return {"message": "Device deactivated successfully"}

        except Exception as e:
            db.rollback()
            logger.error("Failed to deactivate device", device_id=device_id, error=str(e))
            return {"error": "Deactivation failed"}


class ClientOTP:
    """Client-side OTP generator (for testing/simulation)"""
    def __init__(self, derived_key_b64: str):
        self.derived_key = base64.b64decode(derived_key_b64)

    def generate_otp(self) -> int:
        """Generate current TOTP"""
        time_step = int(time.time() // settings.otp_interval)
        msg = struct.pack(">Q", time_step)
        hmac_hash = hmac.new(self.derived_key, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        truncated_hash = hmac_hash[offset:offset + 4]
        code_int = struct.unpack(">I", truncated_hash)[0] & 0x7FFFFFFF
        return code_int % (10 ** settings.otp_digits)
