DEFAULT_LEGAL_DOCUMENT_URL = "https://sss.sk/wp-content/uploads/2026/06/vynimka.pdf"


def default_legal_documents() -> list[dict[str, str]]:
    return [{
        "name": "Vseobecna vynimka pre pohyb mimo vyznacenych chodnikov",
        "url": DEFAULT_LEGAL_DOCUMENT_URL,
    }]
