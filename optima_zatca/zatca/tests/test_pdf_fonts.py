"""Site-free tests for the PDF/A-3 font fetcher (python -m unittest optima_zatca.zatca.tests.test_pdf_fonts)."""

import unittest
from unittest.mock import patch

from optima_zatca.zatca import pdf_fonts


class TestStylesheetFor(unittest.TestCase):
	def test_inter_import_is_served_locally(self):
		# Frappe's print CSS imports Inter from Google Fonts; the PDF must not fetch it.
		with patch.object(pdf_fonts, "inter_css", return_value="LOCAL"):
			url = "https://fonts.googleapis.com/css?family=Inter:400,500,600,700"
			self.assertEqual(pdf_fonts.stylesheet_for(url), "LOCAL")

	def test_other_google_fonts_get_an_empty_stylesheet(self):
		# A font with no local copy must not be fetched either; the format's fallbacks apply.
		self.assertEqual(pdf_fonts.stylesheet_for("https://fonts.googleapis.com/css2?family=Roboto:wght@400"), "")
		self.assertEqual(pdf_fonts.stylesheet_for("https://fonts.gstatic.com/s/inter/v20/x.ttf"), "")

	def test_other_urls_are_left_to_weasyprint(self):
		# Letterheads and images still load as before.
		self.assertIsNone(pdf_fonts.stylesheet_for("file:///srv/fonts/Almarai-Regular.ttf"))
		self.assertIsNone(pdf_fonts.stylesheet_for("http://example.local/files/logo.png"))

	def test_requested_families(self):
		self.assertEqual(
			pdf_fonts.requested_families("https://fonts.googleapis.com/css2?family=Open+Sans:wght@400&family=Inter"),
			["Open Sans", "Inter"],
		)


if __name__ == "__main__":
	unittest.main()
