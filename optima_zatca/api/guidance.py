"""Explainer copy for the onboarding wizard, owned by the server.

It lives here rather than in the client because it is mandate-specific: the stages,
the portal address and the code's lifetime all differ by country, and a second
country should not require a frontend change.

The text is kept short and free of tax jargon on purpose. This is read by whoever
happens to be doing the setup, who is often not the person who understands the
regulation.
"""

from __future__ import annotations

SAUDI_ARABIA = {
    "lifecycle": [
        {
            "key": "keys",
            "title": "A key pair is generated",
            "body": "A private key is created and never leaves this server. Every invoice "
                    "you issue will be signed with it.",
            "actor": "this system",
        },
        {
            "key": "csr",
            "title": "A certificate is requested",
            "body": "The request carries your commercial register, tax number and address, "
                    "and is submitted with the one-time password from the portal.",
            "actor": "this system",
        },
        {
            "key": "compliance",
            "title": "A compliance certificate is issued",
            "body": "This certificate proves the system works. It cannot yet be used for "
                    "real invoices.",
            "actor": "the authority",
        },
        {
            "key": "tests",
            "title": "Six documents are checked",
            "body": "One of every document type you can issue is signed and submitted, so "
                    "the authority can confirm they are valid before trusting real ones.",
            "actor": "the authority",
        },
        {
            "key": "production",
            "title": "The production certificate arrives",
            "body": "From this point your invoices are cleared or reported for real, and "
                    "each one carries a QR code a buyer can verify.",
            "actor": "the authority",
        },
    ],
    "checklist": [
        {
            "key": "tin",
            "title": "Your 15-digit tax number",
            "body": "It begins and ends with 3. Check it on the authority's taxpayer lookup "
                    "before you start.",
        },
        {
            "key": "registers",
            "title": "Every commercial register number",
            "body": "Ten digits each. One certificate is issued per register, so have them "
                    "all to hand.",
        },
        {
            "key": "address",
            "title": "The national address of each register",
            "body": "Building number, street, district, city and postal code. The building "
                    "number is four digits and the postal code five.",
        },
        {
            "key": "arabic",
            "title": "Your legal name in Arabic",
            "body": "Exactly as registered. It is printed on every invoice and embedded in "
                    "the certificate.",
        },
        {
            "key": "otp",
            "title": "A one-time password per register",
            "body": "Generated on the portal. Each is valid for one hour and can be used "
                    "once, so generate them when you reach the last step.",
        },
    ],
    "portalUrl": "https://fatoora.zatca.gov.sa",
    "otpTtlMinutes": 60,
}

BY_COUNTRY = {"SA": SAUDI_ARABIA}


def guidance_for(country_code: str) -> dict:
    """Return the guidance for a country, falling back to Saudi Arabia.

    Falling back rather than failing keeps the explainer page renderable while a
    new country is being added; the wizard's own validation is what refuses an
    unsupported mandate.
    """
    return BY_COUNTRY.get((country_code or "").upper(), SAUDI_ARABIA)
