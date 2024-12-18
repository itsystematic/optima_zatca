import io
import asn1
import uuid
import base64
import frappe
import qrcode
import hashlib
import binascii
from datetime import datetime
from cryptography import x509
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.bindings._rust import ObjectIdentifier
from cryptography.hazmat.primitives import serialization, hashes


def get_company_info(company) -> frappe._dict :
    return frappe.db.get_value("Company" , company , [ "company_name_in_arabic" , "tax_id"] , as_dict=True)


def generate_serial_number(company_name) :
    key =  str(uuid.uuid4())
    return "1-{0}uy|2-{1}nt|3-{2}pu".format(company_name,"ERPNEXT",key[:12])


def generate_common_name():
    return str(uuid.uuid4())


def make_auth_header_for_request(binary_security_token, secret , company_details) :

    authorization = base64.b64encode(f"{binary_security_token}:{secret}".encode()).decode("utf-8")
    company_details['authorization'] = authorization


def create_private_keys(company_details) -> str :

    # Generate the private key using elliptic curve cryptography (SECP256K1)
    private_key = ec.generate_private_key(ec.SECP256K1(), backend=default_backend())
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    return private_key_pem

# @frappe.whitelist(allow_guest=True)
def create_company_csr(settings , company_details:dict):

    if settings.get("check_csr") == 1 :
        company_details.update({
            "egs_serial_number" : settings.get("egs_serial_number") ,
            "common_name" : settings.get("common_name") ,
            "private_key" : settings.get('private_key') ,
            "csr" : settings.get("csr") ,
            "organization_name"  : settings.get("organization_name"),
            "check_csr" : 1
        })
        return settings.get("csr")
    
    company_name_in_arabic  , tax_id = get_company_info(settings.get("company")).values()
    common_name = str(frappe.generate_hash(length=15))
    serial_number = generate_serial_number(company_name_in_arabic)

    company_details["egs_serial_number"] = serial_number
    company_details['common_name'] = common_name

    if settings.api_endpoints == "sandbox":
        customoid = encode_customoid("TESTZATCA-Code-Signing")
    elif settings.api_endpoints == "simulation":
        customoid = encode_customoid("PREZATCA-Code-Signing")
    else:
        customoid = encode_customoid("ZATCA-Code-Signing")
    
    private_key_pem = create_private_keys(company_details)

    company_details["private_key"] = private_key_pem.decode('utf-8')

    private_key = serialization.load_pem_private_key(private_key_pem, password=None, backend=default_backend())

    custom_oid_string = "1.3.6.1.4.1.311.20.2"
    oid = ObjectIdentifier(custom_oid_string)
    custom_extension = x509.extensions.UnrecognizedExtension(oid, customoid) 
    
    dn = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "SA"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, settings.organization_unit_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, company_name_in_arabic),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    alt_name = x509.SubjectAlternativeName([
        x509.DirectoryName(x509.Name([
            x509.NameAttribute(NameOID.SURNAME, serial_number),
            x509.NameAttribute(NameOID.USER_ID, tax_id),
            x509.NameAttribute(NameOID.TITLE, "1100"),
            x509.NameAttribute(ObjectIdentifier("2.5.4.26"), settings.location),
            x509.NameAttribute(NameOID.BUSINESS_CATEGORY, settings.industry),
        ])),
    ])
    
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(dn)
        .add_extension(custom_extension, critical=False)
        .add_extension(alt_name, critical=False)
        .sign(private_key, hashes.SHA256(), backend=default_backend())
    )
    mycsr = csr.public_bytes(serialization.Encoding.PEM)
    base64csr = base64.b64encode(mycsr)
    encoded_string = base64csr.decode('utf-8').strip()

    company_details["csr"] = encoded_string
    company_details["organization_name"] = company_name_in_arabic
    company_details["check_csr"] = 1

    frappe.publish_realtime("zatca" , {"message" :"ZATCA CSR Generated", "indicator" : "green" })

    return encoded_string


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

    certificate_hash = hashlib.sha256(certificate.encode()).hexdigest()
    certificate_encoded = base64.b64encode(certificate_hash.encode())

    company_details['certificate_hash'] = certificate_encoded.decode()
    company_details["public_key"] = public_key_pem
    company_details["issuer_name"] = cert.issuer.rfc4514_string()
    company_details['serial_number509'] = cert.serial_number
    company_details["signature"] = binascii.hexlify(cert.signature).decode("utf-8")


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
