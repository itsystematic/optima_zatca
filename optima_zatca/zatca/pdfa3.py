"""
PDF/A-3 generation module for ZATCA invoices.
Refactored for OOP design and Layout Consistency.
"""

import io
import base64
import pikepdf
from pypdf import PdfWriter
from datetime import datetime

import frappe
from frappe import _
from frappe.utils.pdf import get_file_data_from_writer

from optima_zatca.zatca.utils import log_and_throw_error


@frappe.whitelist()
def generate_pdfa3_for_invoice(sales_invoice_name: str):
    """
    Entry point for the API. Instantiates the generator class.
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
    """
    
    def __init__(self, invoice_name: str):
        self.invoice_name = invoice_name
        self.invoice = frappe.get_doc("Sales Invoice", invoice_name)
        
        if not self.invoice.get("sent_to_zatca"):
            frappe.throw(_("Invoice must be sent to ZATCA before generating PDF/A-3"))
            
        self.zatca_settings = frappe.get_single("Zatca Main Settings")
        self.print_settings = self._get_print_settings()

    def generate_and_save(self):
        """Orchestrates the generation and saving process."""
        
        # 1. Generate the visual PDF (Fixed Layout)
        visual_pdf_bytes = self._generate_visual_pdf()

        # 2. Get the XML Data
        xml_content = self._get_zatca_xml()

        # 3. Combine them using PikePDF
        final_pdf_bytes = self._embed_xml_file(visual_pdf_bytes, xml_content)

        # 4. Save to File Doctype
        return self._save_file(final_pdf_bytes)

    def _get_print_settings(self):
        """Resolves print format, letterhead, and language priorities."""
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
        """
        Generates the visual PDF using the single-step stream method.
        """
        print_format = self.print_settings["print_format"]
        letterhead = self.print_settings["letterhead"]
        
        # 1. Prepare the PDF Writer
        pdf_writer = PdfWriter()
        
        # Optional: Add Metadata
        pdf_writer.add_metadata({
            '/Author': frappe.db.get_value("Global Defaults", None, "default_company") or "Company",
            '/Title': self.invoice.name,
            '/Subject': f"Invoice {self.invoice.name}",
        })

        # 2. Generate PDF directly into the writer
        frappe.get_print(
            doctype=self.invoice.doctype,
            name=self.invoice.name,
            print_format=print_format,
            doc=self.invoice,
            letterhead=letterhead,
            no_letterhead=0 if letterhead else 1,
            as_pdf=True,
            output=pdf_writer
        )

        # 3. Return the bytes
        return get_file_data_from_writer(pdf_writer)

    def _get_zatca_xml(self) -> bytes:
        """Fetch XML from logs."""
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
        Embeds the XML into the PDF using PikePDF manually to ensure PDF/A-3 compliance.
        """
        pdf = pikepdf.Pdf.open(io.BytesIO(pdf_bytes))
        
        # 1. Add Metadata (XMP)
        self._inject_xmp_metadata(pdf)

        # 2. Prepare the XML file for embedding
        filename = f"{self.invoice_name.replace('/', '-')}_zatca.xml"
        
        # --- Manual Embedding Logic ---
        
        # A. Create the Embedded File Stream
        # We use explicit Name constructors starting with '/'
        # MIME types in PDF Names must escape the slash (e.g., text/xml -> /text#2Fxml)
        xml_stream = pikepdf.Stream(pdf, xml_bytes)
        xml_stream.Type = pikepdf.Name("/EmbeddedFile")
        xml_stream.Subtype = pikepdf.Name("/text#2Fxml") 
        
        # Add Params dictionary (ModDate, Size)
        xml_stream.Params = pikepdf.Dictionary(
            Size=len(xml_bytes),
            ModDate=pikepdf.String(datetime.now().strftime("D:%Y%m%d%H%M%S"))
        )

        # B. Create the File Specification Dictionary
        file_spec = pikepdf.Dictionary(
            Type=pikepdf.Name("/Filespec"),
            F=pikepdf.String(filename),
            UF=pikepdf.String(filename),
            Desc=pikepdf.String("ZATCA Invoice XML"),
            # /Data indicates this file is the source data for the visual representation
            AFRelationship=pikepdf.Name("/Data"), 
            EF=pikepdf.Dictionary(
                F=xml_stream 
            )
        )

        # C. Add to /Names/EmbeddedFiles (Standard PDF Attachment)
        if "/Names" not in pdf.Root:
            pdf.Root.Names = pikepdf.Dictionary()
            
        if "/EmbeddedFiles" not in pdf.Root.Names:
            pdf.Root.Names.EmbeddedFiles = pikepdf.Dictionary(
                Names=pikepdf.Array()
            )
            
        # The Names array is a flat list: [name_string, value_obj, name_string, value_obj...]
        pdf.Root.Names.EmbeddedFiles.Names.append(pikepdf.String(filename))
        pdf.Root.Names.EmbeddedFiles.Names.append(file_spec)

        # D. Add to /AF (Associated Files) Array (PDF/A-3 Requirement)
        if "/AF" not in pdf.Root:
            pdf.Root.AF = pikepdf.Array()
            
        pdf.Root.AF.append(file_spec)

        # 3. Save
        output = io.BytesIO()
        pdf.save(output)
        output.seek(0)
        return output.read()

    def _inject_xmp_metadata(self, pdf):
        """
        Injects RDF/XMP metadata required for PDF/A-3.
        """
        metadata = f"""<?xpacket begin='' id='W5M0MpCehiHzreSzNTczkc9d'?>
        <x:xmpmeta xmlns:x='adobe:ns:meta/'>
            <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
                
                <!-- PDF/A Identification -->
                <rdf:Description rdf:about='' xmlns:pdfaid='http://www.aiim.org/pdfa/ns/id/'>
                    <pdfaid:part>3</pdfaid:part>
                    <pdfaid:conformance>B</pdfaid:conformance>
                </rdf:Description>
                
                <!-- Dublin Core Metadata -->
                <rdf:Description rdf:about='' xmlns:dc='http://purl.org/dc/elements/1.1/'>
                    <dc:title>
                        <rdf:Alt>
                            <rdf:li xml:lang='x-default'>{self.invoice_name}</rdf:li>
                        </rdf:Alt>
                    </dc:title>
                    <dc:creator>
                        <rdf:Seq>
                            <rdf:li>Optima ZATCA</rdf:li>
                        </rdf:Seq>
                    </dc:creator>
                    <dc:description>
                        <rdf:Alt>
                            <rdf:li xml:lang='x-default'>ZATCA E-Invoice</rdf:li>
                        </rdf:Alt>
                    </dc:description>
                </rdf:Description>
                
                <!-- XMP Basic -->
                <rdf:Description rdf:about='' xmlns:xmp='http://ns.adobe.com/xap/1.0/'>
                    <xmp:CreateDate>{datetime.now().isoformat()}</xmp:CreateDate>
                    <xmp:ModifyDate>{datetime.now().isoformat()}</xmp:ModifyDate>
                    <xmp:CreatorTool>Frappe Framework</xmp:CreatorTool>
                </rdf:Description>
                
            </rdf:RDF>
        </x:xmpmeta>
        <?xpacket end='w'?>"""

        # Direct assignment to Root.Metadata
        metadata_stream = pdf.make_stream(metadata.encode('utf-8'))
        metadata_stream.Type = pikepdf.Name("/Metadata")
        metadata_stream.Subtype = pikepdf.Name("/XML")
        pdf.Root.Metadata = metadata_stream

    def _save_file(self, content: bytes):
        """Deletes old file and creates new one."""
        
        # Cleanup existing
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