import io
import os
import base64
import mimetypes
import pikepdf
import qrcode
from datetime import datetime

import frappe
from frappe import _, get_app_path
from frappe.utils import get_files_path
from weasyprint import HTML
from optima_zatca.zatca.utils import log_and_throw_error

@frappe.whitelist()
def generate_pdfa3_for_invoice(sales_invoice_name: str):
    """
    Entry point to generate ZATCA-compliant PDF/A-3 for a Sales Invoice.
    """
    try:
        generator = ZatcaPDFA3Generator(sales_invoice_name)
        return generator.generate_and_save()
    except Exception as e:
        log_and_throw_error(
            operation="Generate PDF/A-3 for invoice",
            document_name=sales_invoice_name,
            exception=e
        )

class ZatcaPDFA3Generator:
    """
    Service class to handle the end-to-end generation of ZATCA compliant PDF/A-3.
    It combines Frappe's print format (HTML), WeasyPrint (PDF generation), 
    and PikePDF (XML embedding and Metadata injection).
    """
    
    def __init__(self, invoice_name: str):
        self.invoice_name = invoice_name
        self.invoice = frappe.get_doc("Sales Invoice", invoice_name)
        self.zatca_settings = frappe.get_single("Zatca Main Settings")
        self.print_settings = self._get_print_settings()

    def generate_and_save(self):
        """
        Orchestrates the PDF generation, XML embedding, and file saving.
        """
        # 1. Generate Visual PDF (Raw Bytes from Frappe/WeasyPrint)
        visual_pdf_bytes = self._generate_visual_pdf()

        # 2. Get XML Data
        xml_content = self._get_zatca_xml()

        # 3. Embed XML using PikePDF
        final_pdf_bytes = self._embed_xml_file(visual_pdf_bytes, xml_content)

        # 4. Save to File Doctype
        return self._save_file(final_pdf_bytes)

    def _get_print_settings(self):
        """
        Resolves print settings based on Zatca Settings or defaults.
        """
        return {
            "print_format": (
                self.zatca_settings.get("print_format") or 
                self.invoice.meta.default_print_format or 
                "Standard"
            ),
            "letterhead": (
                self.zatca_settings.get("letter_head") or 
                self.invoice.get("letter_head")
            ),
            "language": (
                self.zatca_settings.get("language") or 
                frappe.local.lang or 
                "en"
            )
        }

    def _get_base64_image(self, filename_or_path, is_private=False):
        """
        Helper to read a file from the filesystem and return a Base64 data string.
        """
        if not filename_or_path:
            return ""

        # Determine path
        if "/" in filename_or_path:
            # It's a URL or full path, extract filename
            filename = filename_or_path.split("/")[-1]
            # Check if private based on URL structure
            if "/private/files/" in filename_or_path:
                is_private = True
        else:
            filename = filename_or_path

        abs_path = get_files_path(filename, is_private=is_private)
        
        if os.path.exists(abs_path):
            mime_type, _ = mimetypes.guess_type(abs_path)
            if not mime_type: 
                mime_type = "image/png"
            
            with open(abs_path, "rb") as img_file:
                b64_string = base64.b64encode(img_file.read()).decode("utf-8")
                return f"data:{mime_type};base64,{b64_string}"
        
        return ""

    def _generate_qr_code(self):
        """
        Returns the ZATCA QR as a `data:` URI.

        The source field holds one of two different things depending on which app
        populated it, and they need opposite treatment:

        * a **TLV/Base64 payload** (`ksa_einv2_qr`, written by the legacy optima
          app) — encode it into a QR here;
        * a **file URL** (`ksa_einv_qr`, declared an Attach Image in
          `setup/customizations.py` and written by `events/sales_invoice.py`) —
          the QR image already exists on disk, so embed it.

        Encoding a URL as if it were a payload yields a QR that scans cleanly and
        carries a filename instead of the invoice TLV, which ZATCA rejects. That
        is silent, so the discrimination below matters.
        """
        qr_data = self.invoice.get("ksa_einv2_qr") or self.invoice.get("ksa_einv_qr")

        if not qr_data:
            return ""

        if qr_data.startswith(("/", "http")):
            return self._get_base64_image(qr_data)

        qr = qrcode.QRCode(
            version=1, 
            error_correction=qrcode.constants.ERROR_CORRECT_L, 
            box_size=10, 
            border=1
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return f"data:image/png;base64,{img_str}"

    def _generate_visual_pdf(self) -> bytes:
        """
        Generates the visual PDF using WeasyPrint.
        Injects fonts, images, and QR codes via string replacement to avoid
        WeasyPrint URL fetch issues in restricted environments.
        """
        # 1. Get Absolute Paths to fonts
        base_font_path = os.path.join(get_app_path("optima_zatca"), "public", "fonts")
        font_path_claudion_regular = "file://" + os.path.join(base_font_path, "Claudion.ttf")
        font_path_marai_regular = "file://" + os.path.join(base_font_path, "Almarai-Regular.ttf")
        font_path_marai_bold = "file://" + os.path.join(base_font_path, "Almarai-Bold.ttf")
        
        # 2. Resolve Letterhead Image
        letterhead_image_src = ""
        letterhead_name = self.print_settings["letterhead"]
        if letterhead_name:
            lh_doc = frappe.get_doc("Letter Head", letterhead_name)
            if lh_doc.image:
                letterhead_image_src = self._get_base64_image(lh_doc.image)

        # 3. Generate QR Code
        qr_code_src = self._generate_qr_code()

        # 4. Resolve Footer Images (Hardcoded filenames as per requirement)
        footer_img_1 = self._get_base64_image("sese_footer-2206.png")
        footer_img_2 = self._get_base64_image("sese_footer-2207.png")
        footer_img_3 = self._get_base64_image("sese_footer-2208.png")

        # 5. Get the HTML from Frappe
        html_content = frappe.get_print(
            doctype=self.invoice.doctype,
            name=self.invoice.name,
            print_format=self.print_settings["print_format"],
            doc=self.invoice,
            no_letterhead=1, 
        )

        # 6. The Magic Linker (Replacements)
        # Fonts
        html_content = html_content.replace("__FONT_REG_CLAUDION_PATH__", font_path_claudion_regular)
        html_content = html_content.replace("__FONT_REG_MARAI_PATH__", font_path_marai_regular)
        html_content = html_content.replace("__FONT_BOLD_MARAI_PATH__", font_path_marai_bold)
        
        # Images
        html_content = html_content.replace("__LETTERHEAD_LOGO_PATH__", letterhead_image_src)
        html_content = html_content.replace("__ZATCA_QR_SRC__", qr_code_src)
        html_content = html_content.replace("__FOOTER_IMG_1__", footer_img_1)
        html_content = html_content.replace("__FOOTER_IMG_2__", footer_img_2)
        html_content = html_content.replace("__FOOTER_IMG_3__", footer_img_3)

        # 7. Generate PDF
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        return pdf_bytes
    
    def _get_zatca_xml(self) -> bytes:
        """
        Retrieves the signed XML content from the Optima Zatca Logs.
        """
        log_entry = frappe.db.get_value(
            "Optima Zatca Logs",
            {
                "reference_doctype": "Sales Invoice",
                "reference_name": self.invoice_name,
                "status": ["in", ["Success", "Warning"]]
            },
            ["xml_content", "invoice"],
            order_by="creation desc",
            as_dict=True
        )
        
        if not log_entry:
            frappe.throw(_("ZATCA XML not found in logs."))
            
        if log_entry.get("xml_content"):
            return log_entry.xml_content.encode("utf-8")
        elif log_entry.get("invoice"):
            return base64.b64decode(log_entry.invoice)
        else:
            frappe.throw(_("ZATCA XML content is empty."))

    def _embed_xml_file(self, pdf_bytes: bytes, xml_bytes: bytes) -> bytes:
        """
        Embeds the XML into the PDF using low-level PikePDF objects to ensure
        PDF/A-3 compliance.
        """
        pdf = pikepdf.Pdf.open(io.BytesIO(pdf_bytes))
        
        # 1. Add Standard Metadata
        company = frappe.db.get_value("Global Defaults", None, "default_company") or "Company"
        with pdf.open_metadata() as meta:
            meta["dc:title"] = self.invoice_name
            meta["dc:creator"] = company
            meta["dc:description"] = "ZATCA E-Invoice"

        # 2. Prepare the XML Stream
        xml_stream = pikepdf.Stream(pdf, xml_bytes)
        
        xml_stream.Type = pikepdf.Name("/EmbeddedFile")
        xml_stream.Subtype = pikepdf.Name("/text#2Fxml") 
        xml_stream.Params = pikepdf.Dictionary(
            Size=len(xml_bytes),
            ModDate=pikepdf.String(datetime.now().strftime("D:%Y%m%d%H%M%S"))
        )

        # 3. Create the File Specification Dictionary
        filename = f"{self.invoice_name.replace('/', '-')}_zatca.xml"
        file_spec = pikepdf.Dictionary(
            Type=pikepdf.Name("/Filespec"),
            F=pikepdf.String(filename),
            UF=pikepdf.String(filename),
            Desc=pikepdf.String("ZATCA Invoice XML"),
            AFRelationship=pikepdf.Name("/Data"), 
            EF=pikepdf.Dictionary(
                F=xml_stream 
            )
        )

        # 4. Add to /Names/EmbeddedFiles
        if "/Names" not in pdf.Root:
            pdf.Root.Names = pikepdf.Dictionary()
            
        if "/EmbeddedFiles" not in pdf.Root.Names:
            pdf.Root.Names.EmbeddedFiles = pikepdf.Dictionary(
                Names=pikepdf.Array()
            )
            
        pdf.Root.Names.EmbeddedFiles.Names.append(pikepdf.String(filename))
        pdf.Root.Names.EmbeddedFiles.Names.append(file_spec)

        # 5. Add to /AF (Associated Files) Array
        if "/AF" not in pdf.Root:
            pdf.Root.AF = pikepdf.Array()
        pdf.Root.AF.append(file_spec)

        # 6. Inject XMP Metadata
        self._inject_xmp_metadata(pdf)

        # 7. Save
        output = io.BytesIO()
        pdf.save(output)
        output.seek(0)
        return output.read()

    def _inject_xmp_metadata(self, pdf):
        """
        Injects RDF/XMP metadata required for PDF/A-3 conformance.
        """
        metadata = f"""<?xpacket begin='' id='W5M0MpCehiHzreSzNTczkc9d'?>
        <x:xmpmeta xmlns:x='adobe:ns:meta/'>
            <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
                <rdf:Description rdf:about='' xmlns:pdfaid='http://www.aiim.org/pdfa/ns/id/'>
                    <pdfaid:part>3</pdfaid:part>
                    <pdfaid:conformance>B</pdfaid:conformance>
                </rdf:Description>
            </rdf:RDF>
        </x:xmpmeta>
        <?xpacket end='w'?>"""

        metadata_stream = pdf.make_stream(metadata.encode('utf-8'))
        metadata_stream.Type = pikepdf.Name("/Metadata")
        metadata_stream.Subtype = pikepdf.Name("/XML")
        pdf.Root.Metadata = metadata_stream

    def _save_file(self, content: bytes):
        """
        Saves the generated PDF to the File doctype and links it to the Invoice.
        """
        # Cleanup existing file to avoid duplicates
        frappe.db.delete("File", {
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": self.invoice_name,
            "attached_to_field": "ksa_einv_pdfa3"
        })

        file_name = f"{self.invoice_name}_PDFA3.pdf".replace("/", "-")
        
        saved_file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "is_private": 0,
            "content": content,
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": self.invoice_name,
            "attached_to_field": "ksa_einv_pdfa3"
        })
        saved_file.save()
        
        # Update Invoice Link
        if hasattr(self.invoice, "ksa_einv_pdfa3"):
            self.invoice.db_set("ksa_einv_pdfa3", saved_file.file_url)
            
        return {
            "file_url": saved_file.file_url,
            "file_name": file_name
        }