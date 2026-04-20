import base64
import unittest
from unittest.mock import MagicMock, patch

from lxml import etree

from optima_zatca.zatca.xml_transport import (
    encode_invoice_xml_for_api,
    get_qr_code_from_cleared_invoice,
    serialize_invoice_xml,
)


class TestSerializeInvoiceXml(unittest.TestCase):
    def test_returns_utf8_xml_bytes(self):
        zatca_xml = MagicMock()
        zatca_xml.root = etree.Element("Invoice")
        zatca_xml.root.text = "test"

        result = serialize_invoice_xml(zatca_xml)

        self.assertIsInstance(result, bytes)
        self.assertIn(b"<Invoice>", result)
        self.assertIn(b"test", result)


class TestEncodeInvoiceXmlForApi(unittest.TestCase):
    def test_returns_valid_base64(self):
        zatca_xml = MagicMock()
        zatca_xml.root = etree.Element("Invoice")
        zatca_xml.root.text = "test"

        result = encode_invoice_xml_for_api(zatca_xml)

        decoded = base64.b64decode(result).decode("utf-8")
        self.assertIn("<Invoice>", decoded)
        self.assertIn("test", decoded)


class TestGetQrCodeFromClearedInvoice(unittest.TestCase):
    def test_returns_fallback_for_non_success_status(self):
        response = MagicMock(status_code=400)

        result = get_qr_code_from_cleared_invoice(response, "generated_qr")

        self.assertEqual(result, "generated_qr")

    def test_returns_fallback_when_cleared_invoice_missing(self):
        response = MagicMock(status_code=200)
        response.json.return_value = {}

        result = get_qr_code_from_cleared_invoice(response, "generated_qr")

        self.assertEqual(result, "generated_qr")

    def test_prefers_qr_code_from_cleared_invoice(self):
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "clearedInvoice": base64.b64encode(b"<Invoice />").decode("utf-8")
        }

        with patch("optima_zatca.zatca.xml_transport.get_qrcode_from_xml") as mock_get_qr:
            mock_get_qr.return_value = "cleared_qr"

            result = get_qr_code_from_cleared_invoice(response, "generated_qr")

        self.assertEqual(result, "cleared_qr")

    def test_returns_fallback_when_xml_has_no_qr(self):
        response = MagicMock(status_code=202)
        response.json.return_value = {
            "clearedInvoice": base64.b64encode(b"<Invoice />").decode("utf-8")
        }

        with patch("optima_zatca.zatca.xml_transport.get_qrcode_from_xml") as mock_get_qr:
            mock_get_qr.return_value = None

            result = get_qr_code_from_cleared_invoice(response, "generated_qr")

        self.assertEqual(result, "generated_qr")
