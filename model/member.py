from datetime import date
from typing import List, Optional
from model.membership import Membership
from utils import decrypt_date
import db # Potrebné pre volanie db_manager
import datetime # Potrebné pre získanie aktuálneho roka

class Member:
    def __init__(self,
                 status: str,
                 title_prefix: str,
                 first_name: str,
                 last_name: str,
                 title_suffix: str,
                 phone: str,
                 email: str,
                 primary_club_id: int,
                 street: Optional[str] = None,
                 city: Optional[str] = None,
                 zip_code: Optional[str] = None,
                 country: Optional[str] = None,
                 encrypted_birth_date: Optional[str] = None,
                 birth_date_obj: Optional[date] = None,
                 is_president: bool = False,
                 discounted_membership: bool = False,
                 ecp_hash: Optional[str] = None,
                 member_id: Optional[int] = None,
                 has_paid_current_year_fee: Optional[bool] = None): # Pridaný nový parameter
        self.member_id = member_id
        self.status = status
        self.title_prefix = title_prefix
        self.first_name = first_name
        self.last_name = last_name
        self.title_suffix = title_suffix
        if birth_date_obj is not None:
            self.birth_date = birth_date_obj
        elif encrypted_birth_date is not None:
            self.birth_date = decrypt_date(encrypted_birth_date)
        else:
            self.birth_date = None
        self.street = street
        self.city = city
        self.zip_code = zip_code
        self.country = country
        self.phone = phone
        self.email = email
        self.ecp_hash = ecp_hash
        self.discounted_membership = discounted_membership
        self.primary_club_id = primary_club_id
        self.memberships: List[Membership] = []
        self.is_president = is_president
        self.has_paid_current_year_fee = has_paid_current_year_fee # Uloženie prednačítanej informácie

    def __repr__(self):
        return f"<Member id={self.member_id} name='{self.first_name} {self.last_name}'>"

    def has_paid_fee(self, year: Optional[int] = None) -> bool:
        """
        Skontroluje, či člen zaplatil poplatok za daný rok.
        Pre aktuálny rok primárne využíva prednačítanú hodnotu.
        """
        if not self.member_id:
            return False
        current_year_value = datetime.datetime.now().year
        year_to_check = year if year is not None else current_year_value

        # Ak sa pýtame na aktuálny rok a máme prednačítanú hodnotu, použijeme ju
        if year_to_check == current_year_value and self.has_paid_current_year_fee is not None:
            return self.has_paid_current_year_fee

        # Fallback: Ak sa pýtame na iný rok, alebo hodnota nebola prednačítaná, urobíme dopyt do DB.
        # Toto by sa v ideálnom prípade pri zobrazovaní zoznamu členov nemalo stať pre aktuálny rok.
        return db.db_manager.has_paid_fee(self.member_id, year_to_check)

    def set_paid_fee(self, year: Optional[int] = None):
        if not self.member_id:
            return
        if year is None:
            year = datetime.datetime.now().year
        # Predpokladáme, že db_manager má metódu na vloženie záznamu o poplatku
        if not self.has_paid_fee(year): # Použijeme vlastnú metódu, ktorá môže využiť cache
            db.db_manager.insert_fee_record(self.member_id, year, self.ecp_hash)
            if year == datetime.datetime.now().year:
                self.has_paid_current_year_fee = True
