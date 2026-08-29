# model/certificate.py
from datetime import date
from typing import Optional


class Certificate:
    def __init__(self,
                 member_id: int,
                 sequence_number: int,
                 name: str,
                 issue_date: date,
                 valid_until: Optional[date] = None,
                 url: Optional[str] = None):
        self.member_id = member_id
        self.sequence_number = sequence_number
        self.name = name
        self.issue_date = issue_date
        self.valid_until = valid_until
        self.url = url

    def __repr__(self):
        return (
            f"<Certificate member_id={self.member_id} "
            f"seq={self.sequence_number} name='{self.name}'>"
        )
