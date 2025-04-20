
from frappe.utils import  get_bench_relative_path
import frappe
import shlex
import subprocess
import time
import base64
from frappe import _
import re
from optima_zatca.zatca.utils import generate_serial_number, get_company_info

FIELDSDESCRIPTION = {
    "C" : "Country Code",
    "O" : "Organization Name",
    "OU" : "Organizational Unit Name",
    "SN" : "Serial Number",
    "UID" : "Unique Identifier",
    "title" : "Title",
    "businessCategory" : "Business Category",
    "registeredAddress" : "Registered Address",
    "emailAddress" : "Email Address",
    "certificateTemplateName" : "Certificate Template Name"
}
class GenerateCSR: 
    
    def __init__(self, settings, site=None, **kwargs ):
        
        self.FIELDSMENDATOY = [ "certificateTemplateName", "emailAddress" , "common_name" , "organization_name" , "organization_unit_name" , "egs_serial_number" , "organization_identifier" , "invoice_type" , "industry" , "address" ]
        
        self.site = site 
        self.company = settings.get("company")
        self.settings = settings
        self.company_details = kwargs
        self.validate()
        self.create_csr_and_private_key()
            
    def validate(self) :
        self.check_company_info()
        self.check_of_fields_mendatory()

    def check_of_fields_mendatory(self) :
        
        for field in self.FIELDSMENDATOY :
            if not self.company_details.get(field) :
                frappe.throw(_("Please Fill the field '{0}' data.").format(FIELDSDESCRIPTION.get(field)))

    def check_company_info(self) :
        if self.settings.api_endpoints == "sandbox" :
            certificateTemplateName = "TESTZATCA-Code-Signing"
        elif self.settings.api_endpoints == "simulation" :
            certificateTemplateName = "PREZATCA-Code-Signing"
        else :
            certificateTemplateName = "ZATCA-Code-Signing"


        self.company_details.update({
            "emailAddress": self.company_details.get("emailAddress") or "test@zatca.com",
            "certificateTemplateName": certificateTemplateName,
        })

    def get_path_name(self) :
        
        return get_bench_relative_path(frappe.local.site) +'/private/files/{0}'.format(self.company.lower().replace(' ', ''))
    
    def create_csr_and_private_key(self) :
        
        self.create_private_key()
        self.create_config_file()
        self.create_csr_key()
        self.create_public_key()
        
        
        
    def create_private_key(self) :
        location = self.get_path_name() + "_PrivateKey.pem"
        command = 'openssl ecparam -name secp256k1 -genkey -noout -out {0}'.format(location) #key location
        self.make_process(command)
        
        
    def create_config_file(self) :
        
        config = """oid_section = OIDS
[ OIDS ]
certificateTemplateName = 1.3.6.1.4.1.311.20.2

[req]
default_bits 	= 2048
emailAddress 	= {emailAddress}
req_extensions	= v3_req
x509_extensions 	= v3_Ca
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn
utf8 = yes

[ dn ]
C= SA
OU= {organization_unit_name}
O= {organization_name}
CN= {common_name}

[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment

[req_ext]
certificateTemplateName = ASN1:PRINTABLESTRING:{certificateTemplateName}
subjectAltName = dirName:alt_names


[alt_names]
SN = {egs_serial_number}
UID = {organization_identifier}
title = {invoice_type}
registeredAddress = {address}
businessCategory = {industry}""".format(**self.company_details)
        
        location = self.get_path_name()
        print(location)
        with open(location + "_config.cnf" , "w" , encoding="utf-8") as file :
            file.write(config)
        
    
    def create_public_key(self) :
        location = self.get_path_name()
        command = "openssl ec -in {0} -pubout -conv_form compressed -out {1}".format(
            location + "_PrivateKey.pem",
            location + "_PublicKey.pem"
        )
        self.make_process(command)
    
    def create_csr_key(self) :
        path = self.get_path_name()
        command = 'openssl req -new -sha256 -key ' + path + '_PrivateKey.pem -extensions v3_req -config ' + path + '_config.cnf -out ' + path + '_csr.pem'
        self.make_process(command)
        time.sleep(5)
        
    
    def read_files(self) -> str :
        
        location = self.get_path_name()
        try :
            
            with ( 
                    open( location + "_PrivateKey.pem" , "r") as private_key_file ,
                    open(location + "_csr.pem" , "r") as csr_key_file ,
                    open(location + "_PublicKey.pem" , "r") as public_key_file
            ) :
                
                private_key = private_key_file.read()
                csr_key = base64.b64encode(csr_key_file.read().encode("utf-8")).decode()
                public_key = public_key_file.read()
        
        except FileNotFoundError as error :
            
            frappe.throw("File not found {0} ".format(error))
            
        except :
            
            frappe.throw("Failed to read files")
        
        return private_key , public_key , csr_key
    
    def get_company_details(self) :

        private_key, public_key, csr_key = self.read_files()
        serial_number = generate_serial_number(self.company)
        common_name = str(frappe.generate_hash(length=15))
        company_name_in_arabic  , tax_id = get_company_info(self.company).values()

        self.company_details.update({
            "private_key" : private_key,
            "public_key" : public_key,
            "csr" : csr_key,
            "egs_serial_number" : serial_number,
            "common_name" : common_name,
            "organization_name"  : company_name_in_arabic,
            "check_csr" : 1
        })
        
        # these were required for creating config file only, if tried to company details in optima zatca setting will throw error
        del self.company_details["emailAddress"] 
        del self.company_details["certificateTemplateName"]

        return self.company_details
    
    def make_process(self , command) :
        time.sleep(5)
        # subprocess.Popen(shlex.split(command), shell=False)
        subprocess.run(shlex.split(command), shell=False)
