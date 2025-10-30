from datetime import date

class Club:
    def __init__(self,
                 club_id: int,
                 name: str,
                 street: str,
                 city: str,
                 zip_code: str,
                 country: str,
                 email: str,
                 phone: str,
                 president_id: int,
                 president_name: str,
                 foundation_date: date,
                 member_count: int,
                 logo_url: str = None):
        self.club_id = club_id
        self.name = name
        self.street = street
        self.city = city
        self.zip_code = zip_code
        self.country = country
        self.email = email
        self.phone = phone
        self.president_id = president_id
        self.president_name = president_name
        self.foundation_date = foundation_date
        self.member_count = member_count
        self.logo_url = logo_url

    def __repr__(self):
        return f"<Club id={self.club_id} name={self.name}>"
