"""Fonts for the PDF/A-3 renderer (WeasyPrint), served from files on this server only.

A print format with a font set (ERPNext's "Sales Invoice Modern with Images" sets Inter) makes
Frappe's print CSS `@import` that font from Google Fonts, and WeasyPrint would fetch it while
building the invoice PDF. `local_font_fetcher` answers those imports itself instead:

- Inter: Frappe's own copy (frappe/public/css/fonts/inter), plus Claudion limited to the Saudi
  Riyal sign (U+20C0, U+FDFC), which Inter lacks; WeasyPrint's glyph fallback then finds it.
- Any other Google font: an empty stylesheet, so the format's own fallbacks apply.

No request leaves the server for a font. Every other URL goes to WeasyPrint's default fetcher.
Arabic in Almarai comes from the "Zatca Sales Invoice" format, which loads Claudion and Almarai
itself (see pdfa3.py). WeasyPrint's fallback for a format that does not name Almarai picks the
server's DejaVu Sans for Arabic, whatever fonts are declared, so nothing here can change that.
"""

import os
from urllib.parse import parse_qs, urlparse

GOOGLE_FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")

RIYAL_RANGE = "U+20C0, U+FDFC"


def _file_url(app, *parts):
	from frappe import get_app_path

	return "file://" + os.path.join(get_app_path(app), "public", *parts)


def requested_families(url):
	"""Font families a Google Fonts CSS URL asks for (css and css2 forms)."""
	query = parse_qs(urlparse(url).query)
	return [family.split(":")[0].replace("+", " ").strip() for family in query.get("family", [])]


def inter_css():
	"""Frappe's local Inter, plus Claudion for the Riyal sign."""
	inter_dir = _file_url("frappe", "css", "fonts", "inter")
	with open(os.path.join(inter_dir.removeprefix("file://"), "inter.css"), encoding="utf-8") as f:
		css = f.read().replace("/assets/frappe/css/fonts/inter", inter_dir)
	claudion = _file_url("optima_zatca", "fonts", "Claudion.ttf")
	return (
		f"{css}\n"
		f'@font-face {{ font-family: "Claudion"; font-style: normal; font-weight: 400; '
		f'src: url("{claudion}") format("truetype"); unicode-range: {RIYAL_RANGE}; }}'
	)


def stylesheet_for(url):
	"""The local stylesheet that replaces a Google Fonts URL, or None for any other URL."""
	host = urlparse(url).hostname or ""
	if host not in GOOGLE_FONT_HOSTS:
		return None
	if host == "fonts.googleapis.com" and "Inter" in requested_families(url):
		return inter_css()
	return ""


def local_font_fetcher(url, *args, **kwargs):
	from weasyprint import default_url_fetcher

	css = stylesheet_for(url)
	if css is None:
		return default_url_fetcher(url, *args, **kwargs)
	return {"string": css, "mime_type": "text/css", "encoding": "utf-8", "redirected_url": url}
