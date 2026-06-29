def normalise_filter_text(value) -> str:
    return " ".join(str(value or "").casefold().split())


def club_filter_values(club) -> list[str]:
    return [
        getattr(club, "name", ""),
        getattr(club, "street", ""),
        getattr(club, "city", ""),
        getattr(club, "zip_code", ""),
        getattr(club, "country", ""),
        getattr(club, "email", ""),
        getattr(club, "phone", ""),
        getattr(club, "webpage", ""),
        getattr(club, "president_name", ""),
        getattr(club, "president_name_text", ""),
        getattr(club, "member_count", ""),
    ]


def club_matches_filter(club, filter_text: str) -> bool:
    terms = normalise_filter_text(filter_text).split()
    if not terms:
        return True

    haystack = normalise_filter_text(" ".join(str(value or "") for value in club_filter_values(club)))
    return all(term in haystack for term in terms)
