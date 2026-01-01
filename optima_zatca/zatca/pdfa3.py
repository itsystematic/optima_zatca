"""
PDF/A-3 generation module for ZATCA invoices.

This module provides functionality to create PDF/A-3 compliant PDFs
with embedded ZATCA XML invoice and regular invoice PDF attachments.
"""

import io
import frappe
from frappe import _
from datetime import datetime
from optima_zatca.zatca.utils import log_and_throw_error
from frappe.utils.weasyprint import PrintFormatGenerator


def generate_pdfa3(sales_invoice: dict, print_format: str = None, letterhead: str = None, language: str = None) -> bytes:
    """
    Main function to generate PDF/A-3 compliant PDF for a Sales Invoice.
    
    Args:
        sales_invoice: Sales Invoice document
        print_format: Print format to use
        letterhead: Letterhead to use
        language: Language for the document
        
    Returns:
        bytes: PDF/A-3 compliant PDF as bytes
        
    """
    print("="*20 + " generate_pdfa3 " + "*"*20)
    print(sales_invoice)
    print("="*50)
    # Get regular PDF with specified format
    regular_pdf = _get_regular_pdf(sales_invoice, print_format, letterhead, language)
    
    
    # Get ZATCA XML
    zatca_xml = _get_zatca_xml(sales_invoice.name)
    
    
    # Create PDF/A-3 with embedded files
    pdfa3_bytes = _create_pdfa3_with_attachments(
        regular_pdf=regular_pdf,
        zatca_xml=zatca_xml,
        invoice_name=sales_invoice.name
    )
    
    return pdfa3_bytes
        
    


def _get_regular_pdf(sales_invoice, print_format: str = None, letterhead: str = None, language: str = None) -> bytes:
    """
    Generate regular invoice PDF using existing WeasyPrint infrastructure.
    
    Args:
        sales_invoice: Sales Invoice document
        print_format: Print format to use
        letterhead: Letterhead to use
        language: Language for the document
        
    Returns:
        bytes: Regular PDF as bytes
    """
    # Use provided print format or fall back to defaults
    if not print_format:
        print_format = sales_invoice.meta.default_print_format or "Standard"
        # Check if Zatca Sales Invoice print format exists
        if frappe.db.exists("Print Format", "Zatca Sales Invoice"):
            print_format = "Zatca Sales Invoice"
    
    # Get print format document to check its type
    print_format_doc = frappe.get_doc("Print Format", print_format)
    
    # Use provided letterhead or fall back to invoice letterhead
    if not letterhead:
        letterhead = sales_invoice.get("letter_head") or None
    
    # Set language context if provided
    if language:
        frappe.local.lang = language
    
    # Check if print format is Jinja-based or uses format_data
    # PrintFormatGenerator only works with format_data-based formats
    # If format_data is None/empty, use frappe.get_print instead
    use_get_print = (
        print_format_doc.print_format_type == "Jinja" or 
        not print_format_doc.format_data or
        print_format_doc.print_format_builder_beta
    )
    
    if use_get_print:
        # Use frappe.get_print for Jinja templates or formats without format_data
        # This approach works for both Jinja and format_data-based formats
        html = frappe.get_print(
            doctype=sales_invoice.doctype,
            name=sales_invoice.name,
            print_format=print_format,
            letterhead=letterhead
        )
        
        # Convert HTML to PDF using WeasyPrint
        from frappe.utils.pdf import get_pdf
        pdf_bytes = get_pdf(html)
        
        return pdf_bytes
    else:
        # Generate PDF using PrintFormatGenerator for format_data-based formats
        generator = PrintFormatGenerator(print_format, sales_invoice, letterhead)
        
        pdf_bytes = generator.render_pdf()
        
        return pdf_bytes
        


def _get_zatca_xml(sales_invoice_name: str) -> bytes:
    """
    Retrieve ZATCA XML invoice from action logs.
    
    Args:
        sales_invoice_name: Name of the Sales Invoice
        
    Returns:
        bytes: ZATCA XML content as bytes
        
    Raises:
        frappe.ValidationError: If XML not found in logs
    """
    # Query the most recent log entry for this invoice
    log_entry = frappe.db.get_value(
        "Optima Zatca Logs",
        {
            "reference_doctype": "Sales Invoice",
            "reference_name": sales_invoice_name,
            "status": ["in", ["Success", "Warning"]]
        },
        ["xml_content", "invoice"],
        order_by="creation desc",
        as_dict=True
    )
    
    if not log_entry:
        frappe.throw(_("ZATCA XML not found in logs. Please ensure invoice was sent to ZATCA."))
    
    # Prefer xml_content field, fallback to base64 decoded invoice field
    if log_entry.get("xml_content"):
        xml_content = log_entry.xml_content
    elif log_entry.get("invoice"):
        # Decode base64 invoice
        import base64
        xml_content = base64.b64decode(log_entry.invoice).decode("utf-8")
    else:
        frappe.throw(_("ZATCA XML content not available in logs."))
    
    # Return as bytes
    return xml_content.encode("utf-8")
        


def _create_pdfa3_with_attachments(
    regular_pdf: bytes,
    zatca_xml: bytes,
    invoice_name: str
) -> bytes:
    """
    Create PDF/A-3 compliant PDF with embedded XML using pikepdf.
    
    Args:
        regular_pdf: Regular invoice PDF as bytes
        zatca_xml: ZATCA XML invoice as bytes
        invoice_name: Name of the invoice for metadata
        
    Returns:
        bytes: PDF/A-3 compliant PDF as bytes
    """
    import pikepdf

    print("="*20 + " zatca_xml " + "*"*20)
    print(f"zatca_xml: {zatca_xml[:100]}... ({len(zatca_xml)} bytes)")
    print("="*50)
    
    # Open the regular PDF
    pdf = pikepdf.Pdf.open(io.BytesIO(regular_pdf))
    
    # Add PDF/A-3 metadata
    _add_pdfa3_metadata(pdf, invoice_name)
    
    # Ensure zatca_xml is bytes
    if isinstance(zatca_xml, str):
        zatca_xml = zatca_xml.encode('utf-8')
    
    # Create embedded file stream for XML
    xml_stream = pikepdf.Stream(pdf, zatca_xml)
    xml_stream.Type = pikepdf.Name.EmbeddedFile
    xml_stream.Subtype = pikepdf.Name("/text#2Fxml")
    
    # Create Params dictionary for the stream
    params_dict = pikepdf.Dictionary()
    params_dict.Size = len(zatca_xml)
    xml_stream.Params = params_dict
    
    # Create embedded files dictionary
    ef_dict = pikepdf.Dictionary()
    ef_dict.F = xml_stream
    
    # Create file specification for the XML
    sanitized_name = invoice_name.replace('/', '-')
    xml_file_spec = pikepdf.Dictionary()
    xml_file_spec.Type = pikepdf.Name.Filespec
    xml_file_spec.F = f"{sanitized_name}_zatca.xml"
    xml_file_spec.UF = f"{sanitized_name}_zatca.xml"
    xml_file_spec.Desc = "ZATCA Invoice XML"
    xml_file_spec.AFRelationship = pikepdf.Name.Data
    xml_file_spec.EF = ef_dict
    
    # Initialize Names dictionary if needed
    if pikepdf.Name.Names not in pdf.Root:
        pdf.Root.Names = pikepdf.Dictionary()
    
    if pikepdf.Name.EmbeddedFiles not in pdf.Root.Names:
        pdf.Root.Names.EmbeddedFiles = pikepdf.Dictionary()
    
    if pikepdf.Name.Names not in pdf.Root.Names.EmbeddedFiles:
        pdf.Root.Names.EmbeddedFiles.Names = pikepdf.Array()
    
    # Add to embedded files (flat array: name, spec, name, spec, ...)
    pdf.Root.Names.EmbeddedFiles.Names.append(f"{sanitized_name}_zatca.xml")
    pdf.Root.Names.EmbeddedFiles.Names.append(xml_file_spec)
    
    # Add to AF array for PDF/A-3 compliance
    if pikepdf.Name.AF not in pdf.Root:
        pdf.Root.AF = pikepdf.Array()
    pdf.Root.AF.append(xml_file_spec)
    
    # Save to bytes
    output = io.BytesIO()
    pdf.save(output)
    output.seek(0)
    
    return output.read()



def _add_pdfa3_metadata(pdf, invoice_name: str) -> None:
    """
    Add required PDF/A-3 metadata to the PDF.
    
    Args:
        pdf: pikepdf.Pdf object
        invoice_name: Name of the invoice for metadata
    """
    import pikepdf
    
    # Create PDF/A-3 metadata
    metadata_xml = f"""<?xpacket begin='' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
    <rdf:Description rdf:about='' xmlns:pdfaid='http://www.aiim.org/pdfa/ns/id/'>
        <pdfaid:part>3</pdfaid:part>
        <pdfaid:conformance>B</pdfaid:conformance>
    </rdf:Description>
    <rdf:Description rdf:about='' xmlns:dc='http://purl.org/dc/elements/1.1/'>
        <dc:title>{invoice_name}</dc:title>
        <dc:creator>Optima ZATCA</dc:creator>
    </rdf:Description>
    <rdf:Description rdf:about='' xmlns:xmp='http://ns.adobe.com/xap/1.0/'>
        <xmp:CreateDate>{datetime.now().isoformat()}</xmp:CreateDate>
        <xmp:ModifyDate>{datetime.now().isoformat()}</xmp:ModifyDate>
    </rdf:Description>
</rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""
    
    # Create metadata stream
    metadata_stream = pdf.make_stream(metadata_xml.encode("utf-8"))
    metadata_stream.Type = pikepdf.Name.Metadata
    metadata_stream.Subtype = pikepdf.Name.XML
    
    # Assign metadata to the PDF root
    pdf.Root.Metadata = metadata_stream
    

