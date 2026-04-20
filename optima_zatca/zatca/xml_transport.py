import base64

from lxml import etree

from optima_zatca.zatca.classes.xml import get_qrcode_from_xml


def serialize_invoice_xml(zatca_xml) -> bytes:
    """Return the invoice XML bytes for transport or logging."""
    return etree.tostring(zatca_xml.root, encoding="utf-8")


def encode_invoice_xml_for_api(zatca_xml) -> str:
    """Encode invoice XML as the ZATCA API payload."""
    return base64.b64encode(serialize_invoice_xml(zatca_xml)).decode("utf-8")


def get_qr_code_from_cleared_invoice(zatca_response, fallback_qr_code: str) -> str:
    """Prefer the QR code embedded in a cleared invoice when available."""
    if zatca_response.status_code not in [200, 202]:
        return fallback_qr_code

    response = zatca_response.json()
    cleared_invoice = response.get("clearedInvoice") if isinstance(response, dict) else None
    if not cleared_invoice:
        return fallback_qr_code

    invoice_xml = base64.b64decode(cleared_invoice).decode("utf-8")
    xml_qrcode = get_qrcode_from_xml(invoice_xml)
    return xml_qrcode or fallback_qr_code
