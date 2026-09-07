from frappe.utils import get_bench_relative_path
import frappe
import shlex
import subprocess
import base64
from frappe import _
from optima_zatca.zatca.utils import generate_serial_number, get_company_info

FIELDS_DESCRIPTION = {
    "certificateTemplateName": "Certificate Template Name",
    "emailAddress": "Email Address",
    "organization_unit_name": "Organizational Unit Name",
    "organization_identifier": "Organization Identifier",
    "invoice_type": "Invoice Type",
    "industry": "Industry",
    "address": "Address"
}

FIELDS_MANDATORY = [
    # "certificateTemplateName",
    # "emailAddress",
    "organization_unit_name",
    "organization_identifier",
    "invoice_type",
    "industry",
    "address"
]

CERTIFICATE_TEMPLATES = {
    # ZATCA's sandbox template is "TSTZATCA", not "TESTZATCA": the portal rejects
    # any other value, and it does so with the same opaque "Invalid Request".
    "sandbox": "TSTZATCA-Code-Signing",
    "simulation": "PREZATCA-Code-Signing",
    "production": "ZATCA-Code-Signing"
}

class GenerateCSR:
    def __init__(self, settings, site=None, **kwargs):
        self.site = site
        self.company = settings.get("company")
        self.settings = settings
        self.company_details = kwargs
        
        self.validate()
        self.generate_required_fields()
        self.create_csr_and_private_key()

    def validate(self):
        self.check_mandatory_fields()
        self.set_certificate_template()

    def check_mandatory_fields(self):
        for field in FIELDS_MANDATORY:
            if not self.company_details.get(field):
                desc = FIELDS_DESCRIPTION.get(field, field)
                frappe.throw(_("Please fill the required field: {0}").format(desc))

    def set_certificate_template(self):
        self.company_details["certificateTemplateName"] = CERTIFICATE_TEMPLATES.get(
            self.settings.api_endpoints, "ZATCA-Code-Signing"
        )

    def generate_required_fields(self):
        """Generate fields required for CSR creation"""
        self.company_details.update({
            "egs_serial_number": generate_serial_number(),
            "common_name": frappe.generate_hash(length=15),
            "emailAddress": get_company_info(self.company).get("email_id", "test@zatca.com"),
        })

    def get_file_path(self, suffix):
        site_path = get_bench_relative_path(self.site or frappe.local.site)
        company_path = self.company.lower().replace(" ", "")
        return f"{site_path}/private/files/{company_path}_{suffix}"

    def create_csr_and_private_key(self):
        """Orchestrate the CSR creation process"""
        try:
            self.create_private_key()
            self.create_config_file()
            self.create_csr()
            self.create_public_key()
        except subprocess.CalledProcessError as e:
            frappe.throw(_("OpenSSL command failed: {0}").format(str(e)))

    def create_private_key(self):
        path = self.get_file_path("PrivateKey.pem")
        self.run_openssl_command(f"ecparam -name secp256k1 -genkey -noout -out {path}")

    def create_config_file(self):
        # One `req_extensions`, naming one section, and that section carries the
        # extensions ZATCA requires.
        #
        # This file used to declare `req_extensions` twice — `v3_req` and then
        # `req_ext` — and OpenSSL takes the first value it sees for a key. So the
        # section it actually used held nothing but basicConstraints and keyUsage,
        # and the certificate template name and subjectAltName that carry the EGS
        # serial, the VAT number, the invoice type, the address and the business
        # category were never written into the request at all. Every compliance
        # CSID call therefore came back `400 Invalid Request`, which says nothing
        # about which field is missing.
        #
        # The layout below matches ZATCA's own published example: the extensions
        # live in `v3_req`, and `create_csr` names it explicitly with `-reqexts`.
        config = f"""oid_section = OIDS
[ OIDS ]
certificateTemplateName = 1.3.6.1.4.1.311.20.2

[req]
default_bits = 2048
emailAddress = {self.company_details.get('emailAddress', 'test@zatca.com')}
req_extensions = v3_req
prompt = no
default_md = sha256
distinguished_name = dn
utf8 = yes
# Arabic organisation names and addresses cannot be held in a PrintableString,
# which is what OpenSSL reaches for by default; without this it silently drops
# the directory-name entries it cannot encode.
string_mask = utf8only

[ dn ]
C= SA
OU= {self.company_details['organization_unit_name']}
O= {self.company_details['organization_name']}
CN= {self.company_details['common_name']}

[ v3_req ]
certificateTemplateName = ASN1:PRINTABLESTRING:{self.company_details['certificateTemplateName']}
subjectAltName = dirName:alt_names

[alt_names]
SN = {self.company_details['egs_serial_number']}
UID = {self.company_details['organization_identifier']}
title = {self.company_details['invoice_type']}
registeredAddress = {self.company_details['address']}
businessCategory = {self.company_details['industry']}"""

        with open(self.get_file_path("config.cnf"), "w", encoding="utf-8") as f:
            f.write(config)

    def create_csr(self):
        key_path = self.get_file_path("PrivateKey.pem")
        config_path = self.get_file_path("config.cnf")
        csr_path = self.get_file_path("csr.pem")
        # `-reqexts`, not `-extensions`: the latter selects extensions for an
        # X.509 certificate, and openssl ignores it when writing a request.
        self.run_openssl_command(
            f"req -new -sha256 -key {key_path} "
            f"-reqexts v3_req -config {config_path} -out {csr_path}"
        )

    def create_public_key(self):
        private_key_path = self.get_file_path("PrivateKey.pem")
        public_key_path = self.get_file_path("PublicKey.pem")
        self.run_openssl_command(
            f"ec -in {private_key_path} -pubout -conv_form compressed -out {public_key_path}"
        )

    def run_openssl_command(self, command):
        full_cmd = f"openssl {command}"
        subprocess.run(
            shlex.split(full_cmd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def get_generated_details(self):
        """Return generated keys and CSR"""
        try:
            with (
                open(self.get_file_path("PrivateKey.pem"), "r") as priv_key,
                open(self.get_file_path("csr.pem"), "r") as csr,
                open(self.get_file_path("PublicKey.pem"), "r") as pub_key
            ):
                return {
                    "private_key": priv_key.read(),
                    "csr": base64.b64encode(csr.read().encode()).decode(),
                    "public_key": pub_key.read(),
                    "egs_serial_number": self.company_details["egs_serial_number"],
                    "common_name": self.company_details["common_name"],
                    "organization_name": self.company_details["organization_name"],
                    "check_csr": 1
                }
        except FileNotFoundError as e:
            frappe.throw(_("File not found: {0}").format(str(e)))
        except Exception as e:
            frappe.throw(_("Error reading generated files: {0}").format(str(e)))