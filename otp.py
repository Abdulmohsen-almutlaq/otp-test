import hmac
import hashlib
import struct
import time

# -------------------------
# SERVER SIDE (setup + verification)
# -------------------------
class Server:
    def __init__(self, master_secret):
        self.master_secret = master_secret

    def generate_derived_key(self, device_id):
        # Generate derived key unique to device
        return hmac.new(self.master_secret, device_id, hashlib.sha256).digest()

    def verify_otp(self, device_id, otp, digits=6, interval=30, window=1):
        # Regenerate derived key for device
        derived_key = self.generate_derived_key(device_id)

        # Check OTP in time window +/- window to allow clock drift
        current_time_step = int(time.time() // interval)
        for offset in range(-window, window + 1):
            time_step = current_time_step + offset
            if self._generate_otp(derived_key, time_step, digits) == otp:
                return True
        return False

    def _generate_otp(self, secret_key, time_step, digits):
        # Pack time step into bytes
        msg = struct.pack(">Q", time_step)
        # HMAC-SHA1 with derived key
        hmac_hash = hmac.new(secret_key, msg, hashlib.sha1).digest()
        # Dynamic truncation
        offset = hmac_hash[-1] & 0x0F
        truncated_hash = hmac_hash[offset:offset + 4]
        code_int = struct.unpack(">I", truncated_hash)[0] & 0x7FFFFFFF
        # Return code modulo digits
        return code_int % (10 ** digits)

# -------------------------
# CLIENT SIDE (offline OTP generation)
# -------------------------
class Client:
    def __init__(self, derived_key):
        self.derived_key = derived_key

    def generate_otp(self, digits=6, interval=30):
        time_step = int(time.time() // interval)
        msg = struct.pack(">Q", time_step)
        hmac_hash = hmac.new(self.derived_key, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        truncated_hash = hmac_hash[offset:offset + 4]
        code_int = struct.unpack(">I", truncated_hash)[0] & 0x7FFFFFFF
        return code_int % (10 ** digits)

# -------------------------
# Simulating the flow
# -------------------------
def main():
    # Server master secret (kept secret)
    master_secret = b"A7F3C94E91D6B1EEB2AA7792DD4F3211"
    device_id = b"DEVICE-XY-123456"

    # Server generates derived key for device (one-time during setup)
    server = Server(master_secret)
    derived_key = server.generate_derived_key(device_id)

    # Client stores derived key (received securely)
    client = Client(derived_key)

    # Client generates OTP
    client_otp = client.generate_otp()
    print(f"Client generated OTP: {client_otp}")

    # Client sends device_id and OTP to server for verification
    is_valid = server.verify_otp(device_id, client_otp)
    print(f"Server verification result: {'Valid' if is_valid else 'Invalid'}")

if __name__ == "__main__":
    main()
