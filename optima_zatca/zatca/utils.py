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
        "address": settings.get("address" , ''),
        # "C": frappe.get_doc("Country", settings.get("country")).code.upper(),
        # "emailAddress" : settings.get("email" , 'test@zatca.com'),
        # "certificateTemplateName" : "ZATCA-Code-Signing" if settings.get("api_endpoints" , '') == "production" else "PREZATCA-Code-Signing"
    })
    
    
    return company_dict

@frappe.whitelist()
def get_prepayment_details(prepayment_invoice, filters=None):
    """
    Fetch prepayment details from the specified prepayment invoice
    """
    try:
        if not prepayment_invoice:
            return []
            
        # Convert string filters to dict if needed
        if filters and isinstance(filters, str):
            filters = frappe.parse_json(filters)
        
        # Build the base filters
        base_filters = {
            "name": prepayment_invoice,
            # "customer": filters.get("customer") if filters else None,
            # "docstatus": 1,  # Only fetch submitted invoices
        }
        
        # Add additional filters if provided
        if filters:
            base_filters.update(filters)
        
        # Fetch prepayment data
        prepayment_data = frappe.get_all(
            "Prepayment Invoice",  # Your doctype name for prepayment invoices
            filters=base_filters,
            fields=[
                "name",
                "issue_date",
                "issue_time", 
                "tax_amount",
                "taxable_amount",
                "tax_category",
                "percent",
                "issue_date",
                "issue_time",
                "uuid",
            ]
        )
        
        return prepayment_data
    except Exception as e:
        frappe.errprint(
            title="Error fetching prepayment details",
            message=f"Error: {str(e)}\nFilters: {filters}"
        )