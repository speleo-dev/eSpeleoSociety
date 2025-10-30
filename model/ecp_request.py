from datetime import date
from typing import Optional

class EcpRequest:
    def __init__(self,
                 request_id: int,
                 member_id: int,
                 photo_hash: str, # Hash of the photo associated with this request (from ecp_records)
                 status: str,
                 request_date: date,
                 approved_ecp_hash: Optional[str] = None): # Final eCP hash if this request is approved
        self.request_id = request_id
        self.member_id = member_id
        self.photo_hash = photo_hash
        self.status = status
        self.request_date = request_date
        self.approved_ecp_hash = approved_ecp_hash

    def __repr__(self):
        return f"<EcpRequest id={self.request_id} status='{self.status}' photo_hash='{self.photo_hash}'>"

    def accept(self):
        from db import db_manager # Moved import inside as it was in original context
        # This method is called after the ECPApprovalDialog handles the core logic.
        # It should reflect the approved state.
        if self.approved_ecp_hash:
            # The request status and approved_ecp_hash in the DB are updated by ECPApprovalDialog.
            # The ecp_records.ecp_hash and ecp_records.ecp_active are also updated there.
            self.status = "approved" # Update local status

    def decline(self):
        from db import db_manager # Moved import inside
        from utils import delete_photo_from_bucket # Moved import inside
        db_manager.update_ecp_request_status(self.request_id, 'rejected') # No approved_ecp_hash here
        # When a request is declined, the associated photo and ecp_record are deleted.
        if self.photo_hash:
            db_manager.delete_ecp_record_by_photo_hash(self.photo_hash) # Deletes from ecp_records
            delete_photo_from_bucket(self.photo_hash) # Deletes from GCS
        member = db_manager.fetch_member_by_id(self.member_id) # fetch_member_by_id expects id
        member.ecp_hash = None
        db_manager.update_member(member)
