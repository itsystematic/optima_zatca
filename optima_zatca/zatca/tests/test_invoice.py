import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


def _load_invoice_module():
    frappe_module = types.ModuleType("frappe")

    def _whitelist(*args, **kwargs):
        def _decorator(function):
            return function

        return _decorator

    frappe_module.whitelist = _whitelist
    frappe_module._ = lambda message: message
    frappe_module.db = MagicMock()
    frappe_module.get_doc = MagicMock()
    frappe_module.msgprint = MagicMock()

    logs_module = types.ModuleType("optima_zatca.zatca.logs")
    logs_module.make_action_log = MagicMock()

    api_module = types.ModuleType("optima_zatca.zatca.api")
    api_module.make_invoice_request = MagicMock()

    invoice_class_module = types.ModuleType("optima_zatca.zatca.classes.invoice")
    invoice_class_module.ZatcaInvoiceData = MagicMock()

    prepayment_module = types.ModuleType("optima_zatca.zatca.prepayment_invoice")
    prepayment_module.create_prepayment_invoice = MagicMock()

    utils_module = types.ModuleType("optima_zatca.zatca.utils")
    utils_module.create_qr_code_for_invoice = MagicMock()
    utils_module.log_and_throw_error = MagicMock()

    patched_modules = {
        "frappe": frappe_module,
        "optima_zatca.zatca.logs": logs_module,
        "optima_zatca.zatca.api": api_module,
        "optima_zatca.zatca.classes.invoice": invoice_class_module,
        "optima_zatca.zatca.prepayment_invoice": prepayment_module,
        "optima_zatca.zatca.utils": utils_module,
    }

    sys.modules.pop("optima_zatca.zatca.invoice", None)
    with patch.dict(sys.modules, patched_modules):
        return importlib.import_module("optima_zatca.zatca.invoice")


class TestFormatZatcaResponse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def test_returns_error_response_with_red_indicator(self):
        response = {
            "validationResults": {
                "errorMessages": [{"message": "First error"}],
                "warningMessages": [],
            }
        }

        result = self.invoice_module.format_zatca_response(response)

        self.assertTrue(result.startswith("🔴"))
        self.assertIn("First error", result)

    def test_returns_warning_response_with_yellow_indicator(self):
        response = {
            "validationResults": {
                "errorMessages": [],
                "warningMessages": [{"message": "First warning"}],
            }
        }

        result = self.invoice_module.format_zatca_response(response)

        self.assertTrue(result.startswith("🟡"))
        self.assertIn("First warning", result)

    def test_returns_success_response_when_no_errors_or_warnings(self):
        response = {"validationResults": {}}

        result = self.invoice_module.format_zatca_response(response)

        self.assertEqual(result, "🟢 Success Invoice")

    def test_includes_all_error_messages_in_output(self):
        response = {
            "validationResults": {
                "errorMessages": [
                    {"message": "First error"},
                    {"message": "Second error"},
                ]
            }
        }

        result = self.invoice_module.format_zatca_response(response)

        self.assertIn("First error", result)
        self.assertIn("Second error", result)


class TestEncodeInvoiceXml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def test_encode_invoice_xml_returns_valid_base64(self):
        from lxml import etree
        import base64

        root = etree.Element("Invoice")
        root.text = "test"
        mock_invoice = MagicMock()
        mock_invoice.xml.root = root

        result = self.invoice_module._encode_invoice_xml(mock_invoice)

        decoded = base64.b64decode(result).decode("utf-8")

        self.assertIn("<Invoice>", decoded)
        self.assertIn("test", decoded)


class TestValidateBeforeSend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def test_validate_before_send_returns_false_on_exception(self):
        mock_invoice = MagicMock()
        mock_invoice.run_method.side_effect = Exception("Validation failed")

        with patch.object(self.invoice_module, "log_and_throw_error") as mock_log:
            result = self.invoice_module._validate_before_send(mock_invoice)

        self.assertFalse(result)
        mock_log.assert_called_once()

    def test_validate_before_send_returns_true_on_success(self):
        mock_invoice = MagicMock()
        mock_invoice.run_method.return_value = None
        mock_invoice.check_permission.return_value = None

        result = self.invoice_module._validate_before_send(mock_invoice)

        self.assertTrue(result)


class TestSubmitToZatcaApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def test_submit_to_zatca_api_calls_make_invoice_request(self):
        mock_invoice = MagicMock()
        mock_invoice.zatca_invoice = {
            "Clearance-Status": "1",
            "UUID": "test-uuid",
            "EndPoint": "https://example.com",
        }
        mock_invoice.company_settings = {"authorization": "Bearer token"}
        mock_invoice.xml.hash = "abc123"

        with patch.object(self.invoice_module, "make_invoice_request") as mock_request:
            mock_request.return_value = MagicMock(status_code=200)

            result = self.invoice_module._submit_to_zatca_api(mock_invoice, "encoded_xml")

        self.assertEqual(result.status_code, 200)
        mock_request.assert_called_once()


class TestUpdateInvoiceDocument(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def test_update_invoice_document_on_success(self):
        mock_invoice_doc = MagicMock()
        mock_invoice_doc.name = "SINV-0001"
        mock_response = MagicMock()
        mock_response.json.return_value = {"clearanceStatus": "CLEARED"}

        with (
            patch.object(self.invoice_module, "create_qr_code_for_invoice") as mock_qr,
            patch.object(self.invoice_module, "frappe"),
        ):
            mock_qr.return_value = "/path/to/qr.png"

            self.invoice_module._update_invoice_document(
                mock_invoice_doc,
                MagicMock(),
                mock_response,
                "qrcode_value",
                True,
            )

        self.assertEqual(mock_invoice_doc.sent_to_zatca, 1)
        self.assertEqual(mock_invoice_doc.clearance_or_reporting, "CLEARED")
        mock_invoice_doc.save.assert_called_once()

    def test_update_invoice_document_on_failure_does_not_save(self):
        mock_invoice_doc = MagicMock()

        with patch.object(self.invoice_module, "frappe"):
            self.invoice_module._update_invoice_document(
                mock_invoice_doc,
                MagicMock(),
                MagicMock(),
                "",
                False,
            )

        mock_invoice_doc.save.assert_not_called()


class TestLogAction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def test_log_action_calls_make_action_log(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.text = ""

        mock_invoice_doc = MagicMock()
        mock_invoice_doc.name = "SINV-0001"
        mock_invoice_doc.get.return_value = ""

        mock_zatca_invoice = MagicMock()
        mock_zatca_invoice.zatca_invoice = {
            "UUID": "uuid",
            "EndPoint": "ep",
            "Environment": "sim",
            "PIH": "pih",
            "InvoiceCounter": 1,
        }
        mock_zatca_invoice.xml.hash = "hash"
        mock_zatca_invoice.xml.qr_code = "qr"
        mock_zatca_invoice.xml.root = MagicMock()

        with (
            patch.object(self.invoice_module, "etree") as mock_etree,
            patch.object(self.invoice_module, "make_action_log") as mock_log,
        ):
            mock_etree.tostring.return_value = b"<xml/>"

            self.invoice_module._log_action(
                mock_invoice_doc,
                mock_zatca_invoice,
                mock_response,
                "encoded",
                "qrcode",
                True,
            )

        mock_log.assert_called_once()


class TestHandlePostSuccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def test_handle_post_success_skips_on_failure(self):
        with (
            patch.object(
                self.invoice_module.prepayment_invoice,
                "create_prepayment_invoice",
            ) as mock_prepayment,
            patch.object(self.invoice_module, "frappe"),
        ):
            self.invoice_module._handle_post_success(MagicMock(), MagicMock(), False)

        mock_prepayment.assert_not_called()

    def test_handle_post_success_auto_submits_when_flag_is_false(self):
        mock_invoice_doc = MagicMock()
        mock_invoice_doc.get.return_value = "Normal"

        mock_invoice = MagicMock()
        mock_invoice.zatca_invoice = {"UUID": "uuid"}

        with (
            patch.object(
                self.invoice_module.prepayment_invoice,
                "create_prepayment_invoice",
            ) as mock_prepayment,
            patch.object(self.invoice_module, "frappe") as mock_frappe,
        ):
            mock_frappe.db.get_single_value.return_value = 0

            self.invoice_module._handle_post_success(mock_invoice_doc, mock_invoice, True)

        mock_prepayment.assert_not_called()
        mock_invoice_doc.submit.assert_called_once()
        mock_frappe.db.commit.assert_called_once()

    def test_handle_post_success_skips_submit_when_manual_flag_is_true(self):
        mock_invoice_doc = MagicMock()
        mock_invoice_doc.get.return_value = "Normal"

        with (
            patch.object(
                self.invoice_module.prepayment_invoice,
                "create_prepayment_invoice",
            ) as mock_prepayment,
            patch.object(self.invoice_module, "frappe") as mock_frappe,
        ):
            mock_frappe.db.get_single_value.return_value = 1

            self.invoice_module._handle_post_success(mock_invoice_doc, MagicMock(), True)

        mock_prepayment.assert_not_called()
        mock_invoice_doc.submit.assert_not_called()


class TestSendToZatcaOrchestrator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoice_module = _load_invoice_module()

    def test_send_to_zatca_orchestrates_all_helpers(self):
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_invoice = MagicMock()
        mock_invoice.xml.qr_code = "qr"

        with (
            patch.object(self.invoice_module, "frappe") as mock_frappe,
            patch.object(self.invoice_module, "ZatcaInvoiceData") as mock_zatca_cls,
            patch.object(self.invoice_module, "_validate_before_send") as mock_validate,
            patch.object(self.invoice_module, "_encode_invoice_xml") as mock_encode,
            patch.object(self.invoice_module, "_submit_to_zatca_api") as mock_submit,
            patch.object(self.invoice_module, "_update_invoice_document") as mock_update,
            patch.object(self.invoice_module, "_log_action") as mock_log,
            patch.object(self.invoice_module, "_handle_post_success") as mock_post,
        ):
            mock_frappe.get_doc.return_value = MagicMock()
            mock_validate.return_value = True
            mock_encode.return_value = "encoded"
            mock_submit.return_value = mock_response
            mock_zatca_cls.return_value = mock_invoice

            result = self.invoice_module.send_to_zatca("SINV-0001")

        self.assertTrue(result)
        mock_validate.assert_called_once()
        mock_encode.assert_called_once()
        mock_submit.assert_called_once()
        mock_update.assert_called_once()
        mock_log.assert_called_once()
        mock_post.assert_called_once()

    def test_send_to_zatca_returns_false_when_validation_fails(self):
        with (
            patch.object(self.invoice_module, "frappe") as mock_frappe,
            patch.object(self.invoice_module, "ZatcaInvoiceData") as mock_zatca_cls,
            patch.object(self.invoice_module, "_validate_before_send") as mock_validate,
            patch.object(self.invoice_module, "_encode_invoice_xml") as mock_encode,
        ):
            mock_frappe.get_doc.return_value = MagicMock()
            mock_validate.return_value = False

            result = self.invoice_module.send_to_zatca("SINV-0001")

        self.assertFalse(result)
        mock_zatca_cls.assert_not_called()
        mock_encode.assert_not_called()
