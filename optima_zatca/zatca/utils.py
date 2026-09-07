import io
import asn1
import uuid
import base64
import frappe
import qrcode
import hashlib
import binascii
import traceback
from frappe import _
from datetime import datetime
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import serialization, hashes


def get_company_info(company) -> frappe._dict :
    return frappe.db.get_value("Company" , company , [ "company_name_in_arabic" , "tax_id"] , as_dict=True)


def generate_serial_number(company_name) :
    key =  str(uuid.uuid4())
    return "1-{0}uy|2-{1}nt|3-{2}pu".format(key[:12],"ERPNEXT",key[:12])


def generate_common_name():
    return str(uuid.uuid4())


def make_auth_header_for_request(binary_security_token, secret) :
    return base64.b64encode(f"{binary_security_token}:{secret}".encode()).decode("utf-8")


def create_private_keys(company_details) -> str :

    # Generate the private key using elliptic curve cryptography (SECP256K1)
    private_key = ec.generate_private_key(ec.SECP256K1(), backend=default_backend())
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    return private_key_pem

def encode_customoid(custom_string):
    # Create an encoder
    encoder = asn1.Encoder()
    encoder.start()
    encoder.write(custom_string, asn1.Numbers.UTF8String)
    return encoder.output()


def extract_details_from_certificate(certificate , company_details:dict):
    
    cert_base64 = """
    -----BEGIN CERTIFICATE-----
    {base_64}
    -----END CERTIFICATE-----
    """.format(base_64=certificate.strip())
    
    cert = x509.load_pem_x509_certificate(cert_base64.encode(), default_backend())
    public_key = cert.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()  

    isser_name = get_isser_name(cert.issuer.rfc4514_string()) # return with comma + space separated string

    certificate_hash = hashlib.sha256(certificate.encode()).hexdigest()
    certificate_encoded = base64.b64encode(certificate_hash.encode())

    company_details['certificate_hash'] = certificate_encoded.decode()
    company_details["public_key"] = public_key_pem
    company_details["issuer_name"] = isser_name
    company_details['serial_number509'] = cert.serial_number
    company_details["signature"] = binascii.hexlify(cert.signature).decode("utf-8")

def get_isser_name(certificate: str) -> str:
    """ Function To Get Issuer Name in comma + space separated string """
    parts = certificate.split(',')
    return ', '.join(parts)

def load_private_key(string_private_key):
    """ Function Return private key After Serialization """
    private_key = serialization.load_pem_private_key(string_private_key.encode('utf-8'),password=None)
    return private_key


def sign_invoice(string_private_key,invoice_hash):

    message_hash = bytes.fromhex(invoice_hash)
    private_key = load_private_key(string_private_key)
    sign =  private_key.sign(message_hash, ec.ECDSA(hashes.SHA256()))
    current_timestamp = datetime.now()
    formatted_timestamp = current_timestamp.strftime("%Y-%m-%dT%H:%M:%S")
    sign_enc = base64.b64encode(sign).decode('utf-8')
    
    return sign_enc , formatted_timestamp


def format_datetime(date, time):
    
    if not isinstance(date, str):
        date = str(date)
        
    if not isinstance(time, str):
        time = str(time)
    
    DateTime = date + ' ' + time
    DateTimeFormat = DateTime.split('.')[0]
    # make the time into date time format string
    old_format_date = datetime.strptime(DateTimeFormat, '%Y-%m-%d %H:%M:%S')
    # make it iso
    formatted_date = old_format_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return formatted_date


def get_address_of_company(commercial_register):

    """ Handle To Get Address of Company """
    filters = []
    if commercial_register.is_main_commercial_register_for_the_company :

        filters.append([""])

    return frappe.get_doc("Address" , filters )

def create_address(commercial_register, **kwargs):
    if not frappe.db.exists("Address", {"address_title": "{0}-Billing".format(kwargs.get("commercial_register"))}):
        address = frappe.get_doc(
            {
                "doctype": "Address",
                "address_title": kwargs.get("commercial_register"),
                "address_type": "Billing",
                "building_no" : kwargs.get("building_no"),
                "address_line1": kwargs.get("address_line1"),
                "city": kwargs.get("city"),
                "district": kwargs.get("district"),
                "country": "Saudi Arabia",
                "address_line2": kwargs.get("address_line2"),
                "short_address" : kwargs.get("short_address"),
                "links": [{"link_doctype": "Commercial Register", "link_name": commercial_register.name }],
            }
        ).insert(ignore_permissions=True)
        return address

    return frappe.get_doc("Address", {"address_title": "{0}-Billing".format(kwargs.get("commercial_register"))})

def create_commercial_register(**kwargs):
    
    if not frappe.db.exists("Commercial Register", kwargs.get("commercial_register")):
        commercial_register = frappe.get_doc(
            {
                "doctype": "Commercial Register",
                "commercial_register_name" : kwargs.get("commercial_register"),
                "address" : kwargs.get("address"),
                "tax_id" : kwargs.get("tax_id"),
                "location" : kwargs.get("location"),
            }
        ).insert(ignore_permissions=True)

        return commercial_register
    
    return frappe.get_doc("Commercial Register", kwargs.get("commercial_register"))




def generate_qr_code(
    seller_name ,
    seller_vat ,
    invoice_date , 
    invoice_time , 
    invoice_total , 
    vat_total , 
    invoice_hash , 
    invoice_signature , 
    public_key_str , 
    signature_ecdsa
) :

    # Remove the last character Z from invoice_timestamp
    invoice_timestamp = format_datetime(invoice_date , invoice_time)[:-1]
    # Remove Words Start and End
    public_key_str = public_key_str.replace("-----BEGIN PUBLIC KEY-----\n", "")
    public_key_str = public_key_str.replace("-----END PUBLIC KEY-----", "")
    
    concatenated_data = (
        bytes([1]) + bytes([len(seller_name.encode('utf-8'))]) + seller_name.encode("utf-8") +
        bytes([2]) + bytes([len(seller_vat.encode('utf-8'))]) + seller_vat.encode("utf-8") +
        bytes([3]) + bytes([len(invoice_timestamp)]) + invoice_timestamp.encode("utf-8") +
        bytes([4]) + bytes([len(invoice_total)]) + invoice_total.encode("utf-8") +
        bytes([5]) + bytes([len(vat_total)]) + vat_total.encode("utf-8") +
        bytes([6]) + bytes([len(invoice_hash)]) + invoice_hash.encode("utf-8") +
        bytes([7]) + bytes([len(invoice_signature)]) + invoice_signature.encode("utf-8") +
        bytes([8]) + bytes([len(base64.b64decode(public_key_str))]) + base64.b64decode(public_key_str) +
        bytes([9]) + bytes([len(bytes.fromhex(signature_ecdsa))]) + bytes.fromhex(signature_ecdsa)
    )
    
    # qr code is the base46 encoding of the concated array
    qrcode_encode = base64.b64encode(concatenated_data).decode()

    return qrcode_encode


def create_qr_code_for_invoice(invoice_id , qrcode_encode):

    img = qrcode.make(qrcode_encode)
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format="PNG" ,optimize=True)
    img_content = img_byte_array.getvalue()

    frappe.db.delete("File", {"attached_to_doctype": "Sales Invoice", "attached_to_name": invoice_id , "attached_to_field": "ksa_einv_qr"})

    invoice_qrcode = frappe.get_doc({
        "doctype": "File",
        "file_name":  f"{invoice_id}.png",
        "is_private": 0,
        "content": img_content,
        "attached_to_doctype": "Sales Invoice",
        "attached_to_name": invoice_id,
        "attached_to_field": "ksa_einv_qr",
    })
    invoice_qrcode.save()
    return invoice_qrcode.file_url

def format_registered_address(settings) -> str:
    """The registered address as one ASCII line, for the CSR's subjectAltName.

    Two problems are solved here, both of which left the request missing fields
    ZATCA requires.

    The `address` field on the setting is a Link, so its value is the Address
    document's *name* — something like "My Company (Demo) المدينه - شوران-Billing".
    That was going into the request verbatim.

    And a directory-name entry cannot hold Arabic. OpenSSL reads the config as
    Latin-1 and re-encodes, so Arabic comes back as mojibake; combined with the
    commas of a formatted address it fails to encode the entry at all, and drops
    `businessCategory` behind it. The subject DN is unaffected — it carries the
    Arabic organisation name correctly — so this restriction applies only here.

    Everything non-ASCII is therefore transliterated away. What remains is the
    part of an address that is ASCII anyway: building number, postal code and any
    Latin street or city name. Falls back to the building number, so this can
    shorten the address but never empty it — an absent `registeredAddress` is
    refused outright.
    """
    address_name = settings.get("address") or ""
    parts = []

    if address_name and frappe.db.exists("Address", address_name):
        address = frappe.db.get_value(
            "Address",
            address_name,
            ["building_no", "address_line1", "district", "city", "pincode"],
            as_dict=True,
        ) or {}
        parts = [
            address.get("building_no"),
            address.get("address_line1"),
            address.get("district"),
            address.get("city"),
            address.get("pincode"),
        ]

    line = " ".join(
        ascii_only(part) for part in parts if part and ascii_only(part)
    ).strip()

    return line or ascii_only(settings.get("location")) or "NA"


def ascii_only(value) -> str:
    """Drop what a directory string cannot hold, and collapse the gaps.

    Commas go too: OpenSSL treats a comma in a `dirName` value as a separator and
    the entry is lost.
    """
    if not value:
        return ""
    kept = "".join(
        character
        for character in str(value)
        if character.isascii() and (character.isalnum() or character in " -_/.")
    )
    return " ".join(kept.split())


def get_company_data_to_config(settings:dict={}, company_dict: dict={}) -> dict :
    
    company = frappe.get_doc("Company", settings.get("company"))
    key = ( company.get("abbr") or "TNT-" ) + str(uuid.uuid4())
    
    company_dict.update({
        # "CN": company.get("common_name" , ''),
        "common_name" :key,
        "organization_name": settings.get("organization_name" , '') ,
        "organization_unit_name": settings.get("organization_unit_name" , ''),
        # "SN": settings.get("sn" , ''),
        "egs_serial_number" : "1-{0}uy|2-{1}nt|3-{2}pu".format(key[:12],"ERPNEXT",key[:12]),
        "organization_identifier": company.get("tax_id" , ''),
        "invoice_type": settings.get("invoice_type" , ''),
        "industry": settings.get("industry" , ''),
        "address": format_registered_address(settings),
        # "C": frappe.get_doc("Country", settings.get("country")).code.upper(),
        # "emailAddress" : settings.get("email" , 'test@zatca.com'),
        # "certificateTemplateName" : "ZATCA-Code-Signing" if settings.get("api_endpoints" , '') == "production" else "PREZATCA-Code-Signing"
    })
    
    
    return company_dict

@frappe.whitelist()
def get_prepayment_details(prepayment_invoice, filters=None):
    """
    Fetch prepayment details from the specified prepayment invoice.
    
    Args:
        prepayment_invoice: The name of the prepayment invoice to fetch
        filters: Optional additional filters as string or dict
        
    Returns:
        List of prepayment invoice details
    """
    try:
        if not prepayment_invoice:
            return []
            
        # Convert string filters to dict if needed
        if filters and isinstance(filters, str):
            filters = frappe.parse_json(filters)
        
        # Fetch the prepayment invoice directly by name
        prepayment_data = frappe.get_doc("Prepayment Invoice", prepayment_invoice)
        
        # Start building the result list
        result_list = [prepayment_data]
        
        # Recursively fetch previous prepayment invoices if they exist
        # Check both has_previous_prepayment flag and that previous_prepayment_invoice is not null/empty
        if (prepayment_data.get("has_previous_prepayment") and 
            prepayment_data.get("previous_prepayment_invoice")):
            
            previous_invoices = get_prepayment_details(
                prepayment_data.get("previous_prepayment_invoice"), 
                filters
            )
            # Extend the list with previous prepayment details
            result_list.extend(previous_invoices)
            
        return result_list
        
    except Exception as e:
        log_and_throw_error(
            operation="fetch prepayment details for",
            document_name=prepayment_invoice,
            exception=e,
            custom_message="Failed to fetch prepayment invoice details. Please check the Error Log."
        )


def log_and_throw_error(operation: str, document_name: str, exception: Exception, custom_message: str = None) -> None:
    """
    Log an error to the error log and throw a user-friendly message.
    
    Args:
        operation: The operation that failed (e.g., "create", "update", "delete")
        document_name: The name/ID of the document being processed
        exception: The exception that was caught
        custom_message: Optional custom error message to display to the user
    
    Raises:
        frappe.ValidationError: A user-friendly error message
    """
    error_message = str(exception)
    error_trace = traceback.format_exc()
    
    # Generate the log title
    log_title = f"Failed to {operation} {document_name}"
    
    # Log the detailed error
    frappe.log_error(
        title=log_title,
        message=f"Error: {error_message}\n{error_trace}"
    )
    
    # Use custom message if provided, otherwise create a generic one
    user_message = custom_message or f"Failed to {operation}. Please check the Error Log."
    
    # Throw the user-friendly message
    frappe.throw(_(user_message))


@frappe.whitelist()
def get_item_details(args, doc=None, for_validate=False, overwrite_warehouse=True):
	"""
	Custom get_item_details for optima_zatca that adds customer group income account for prepayment sales invoices
     to make it work with muiltiple CURRANCY invoices.
	"""
	from erpnext.stock.get_item_details import get_item_details as erpnext_get_item_details

	# Parse args if it's a string (when called via API)
	if isinstance(args, str):
		args = frappe.parse_json(args)

	# Call the standard ERPNext function
	item_details = erpnext_get_item_details(args, doc, for_validate, overwrite_warehouse)

	# Custom logic for prepayment sales invoices
	prepayment_types = ["Initial Prepayment", "Prepayment"]
	if args.get("doctype") == "Sales Invoice" and args.get("sales_invoice_type") in prepayment_types:
		# Get customer group income account
		customer_group = None
		if args.get("customer"):
			customer_group = frappe.db.get_value("Customer", args.get("customer"), "customer_group")
		
		if customer_group:
			customer_group_income_account = frappe.db.get_value(
				"Party Account", 
				{"parent": customer_group, "company": args.get("company")}, 
				"advance_account"
			)
			
			if customer_group_income_account:
				item_details["income_account"] = customer_group_income_account
				# Add flag to indicate this is a custom income account
				item_details["__is_custom_income_account"] = True

	return item_details