from typing import Optional
from utils import create_check_hash, verify_check_hash

class Ecp:
    def __init__(self,
                 ecp_hash: str,
                 gdpr_consent: bool,
                 notifications_enabled: bool,
                 photo_hash: str,
                 is_ecp_active: bool,
                 member_id: Optional[int],
                 check_hash: Optional[str] = None,
                 ecp_id: Optional[int] = None,
                 qr_url: Optional[str] = None,
                 qr_key_id: Optional[str] = None,
                 qr_payload_hash: Optional[str] = None,
                 issued_at=None,
                 valid_until=None,
                 wallet_status: Optional[str] = None,
                 wallet_object_id: Optional[str] = None,
                 wallet_last_error: Optional[str] = None):
        self.ecp_id = ecp_id
        self.ecp_hash = ecp_hash
        self.gdpr_consent = gdpr_consent
        self.notifications_enabled = notifications_enabled
        self.photo_hash = photo_hash
        self.is_ecp_active = is_ecp_active
        self.member_id = member_id
        self.qr_url = qr_url
        self.qr_key_id = qr_key_id
        self.qr_payload_hash = qr_payload_hash
        self.issued_at = issued_at
        self.valid_until = valid_until
        self.wallet_status = wallet_status
        self.wallet_object_id = wallet_object_id
        self.wallet_last_error = wallet_last_error
        if check_hash and verify_check_hash(check_hash):
            self.check_hash = check_hash
        else:
            self.check_hash = create_check_hash()

    def __repr__(self):
        return f"<Ecp hash={self.ecp_hash} active={self.is_ecp_active}>"
