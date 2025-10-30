class Membership:
    def __init__(self,
                 club_id: int,
                 member_id: int,
                 club_name: str,
                 president_id: int, # Club's president ID
                 is_primary_club: bool):
        self.club_id = club_id
        self.member_id = member_id
        self.club_name = club_name
        self.president_id = president_id
        self.is_primary_club = is_primary_club

    def __repr__(self):
        return f"<Membership club_id={self.club_id} member_id={self.member_id} primary={self.is_primary_club}>"
