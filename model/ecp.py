from typing import Optional
from utils import create_check_hash, verify_check_hash

class Ecp:
    def __init__(self,
                 ecp_hash: str,
                 gdpr_consent: bool,
                 notifications_enabled: bool,
                 photo_hash: str,
                 is_ecp_active: bool,
                 member_id: int,
                 check_hash: Optional[str] = None,
                 ecp_id: Optional[int] = None):
        self.ecp_id = ecp_id
        self.ecp_hash = ecp_hash
        self.gdpr_consent = gdpr_consent
        self.notifications_enabled = notifications_enabled
        self.photo_hash = photo_hash
        self.is_ecp_active = is_ecp_active
        self.member_id = member_id
        if check_hash and verify_check_hash(check_hash):
            self.check_hash = check_hash
        else:
            self.check_hash = create_check_hash()

    def __repr__(self):
        return f"<Ecp hash={self.ecp_hash} active={self.is_ecp_active}>"
