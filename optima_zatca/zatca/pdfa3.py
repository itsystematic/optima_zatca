import io
import base64
import mimetypes
import pikepdf
from datetime import datetime

import frappe
from frappe import _

from optima_zatca.zatca.utils import log_and_throw_error

@frappe.whitelist()
def generate_pdfa3_for_invoice(sales_invoice_name: str):
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
    """
    
    def __init__(self, invoice_name: str):
        self.invoice_name = invoice_name
        self.invoice = frappe.get_doc("Sales Invoice", invoice_name)
        
        # Commented out for visual debugging (optional)
        # if not self.invoice.get("sent_to_zatca"):
        #     frappe.throw(_("Invoice must be sent to ZATCA before generating PDF/A-3"))
            
        self.zatca_settings = frappe.get_single("Zatca Main Settings")
        self.print_settings = self._get_print_settings()

    def generate_and_save(self):
        # 1. Generate Visual PDF (Raw Bytes from Frappe/WeasyPrint)
        visual_pdf_bytes = self._generate_visual_pdf()

        # ============================================================
        # DEBUGGING MODE: XML EMBEDDING DISABLED
        # ============================================================
        
        # 2. Get XML Data
        xml_content = self._get_zatca_xml()

        # 3. Embed XML using PikePDF (Manual Method for Compatibility)
        final_pdf_bytes = self._embed_xml_file(visual_pdf_bytes, xml_content)

        # 4. Save to File Doctype (Saving the VISUAL bytes directly)
        return self._save_file(final_pdf_bytes)

    def _get_print_settings(self):
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


    def _generate_visual_pdf(self) -> bytes:
        import os
        from frappe import get_app_path
        from frappe.utils import get_files_path
        from weasyprint import HTML

        # 1. Get Absolute Paths to fonts
        font_path_claudion_regular = "file://" + os.path.join(get_app_path("optima_zatca"), "public", "fonts", "Claudion.ttf")
        font_path_marai_regular = "file://" + os.path.join(get_app_path("optima_zatca"), "public", "fonts", "Almarai-Regular.ttf")
        font_path_marai_bold = "file://" + os.path.join(get_app_path("optima_zatca"), "public", "fonts", "Almarai-Bold.ttf")
        
        # 2. RESOLVE LETTERHEAD IMAGE
        letterhead_name = self.print_settings["letterhead"]
        letterhead_image_src = "" 
        
        if letterhead_name:
            lh_doc = frappe.get_doc("Letter Head", letterhead_name)
            
            if lh_doc.image:
                # --- FIX START ---
                file_url = lh_doc.image # e.g., "/files/sESE.png"
                
                # 1. Extract just the filename ("sESE.png")
                filename = file_url.split("/")[-1]
                
                # 2. Determine if it is Private or Public based on the URL
                is_private = "/private/files/" in file_url
                
                # 3. Get the correct absolute path
                abs_path = get_files_path(filename, is_private=is_private)
                # --- FIX END ---

                print(f"DEBUG: Attempting to load image from: {abs_path}")

                if os.path.exists(abs_path):
                    # Guess MIME type (png/jpg)
                    mime_type, _ = mimetypes.guess_type(abs_path)
                    if not mime_type: 
                        mime_type = "image/png"

                    # Read file and convert to Base64
                    with open(abs_path, "rb") as img_file:
                        b64_string = base64.b64encode(img_file.read()).decode("utf-8")
                        letterhead_image_src = f"data:{mime_type};base64,{b64_string}"
                else:
                    print(f"DEBUG: Image file STILL not found at {abs_path}")

        # 3. Get the HTML from Frappe
        html_content = frappe.get_print(
            doctype=self.invoice.doctype,
            name=self.invoice.name,
            print_format=self.print_settings["print_format"],
            doc=self.invoice,
            # We pass no_letterhead=1 because we are handling the logo manually above
            no_letterhead=1, 
        )

        # 4. The Magic Linker (Replacements)
        # Fonts
        html_content = html_content.replace("__FONT_REG_CLAUDION_PATH__", font_path_claudion_regular)
        html_content = html_content.replace("__FONT_REG_MARAI_PATH__", font_path_marai_regular)
        html_content = html_content.replace("__FONT_BOLD_MARAI_PATH__", font_path_marai_bold)
        
        # Letterhead Image
        # If no image found, we replace with empty string (or a transparent pixel data uri if you prefer)
        html_content = html_content.replace("__LETTERHEAD_LOGO_PATH__", letterhead_image_src)

        # 5. Generate PDF
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        return pdf_bytes
    

    def _get_zatca_xml(self) -> bytes:
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
        Embeds the XML into the PDF using low-level PikePDF objects.
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
        Injects RDF/XMP metadata required for PDF/A-3.
        """
        # We construct a minimal XMP packet that declares PDF/A-3B conformance
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

        # Create a metadata stream and attach it to Root
        metadata_stream = pdf.make_stream(metadata.encode('utf-8'))
        metadata_stream.Type = pikepdf.Name("/Metadata")
        metadata_stream.Subtype = pikepdf.Name("/XML")
        pdf.Root.Metadata = metadata_stream

    def _save_file(self, content: bytes):
        # Cleanup existing file
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