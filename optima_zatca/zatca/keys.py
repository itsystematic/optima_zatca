
from frappe.utils import  get_bench_relative_path
import frappe
import shlex
import subprocess
import time
import base64
from frappe import _
import re


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
    
    def __init__(self, company, site=None ):
        
        self.FIELDSMENDATOY = [ "CN" , "O" , "OU" , "SN" , "UID" , "title" , "businessCategory" , "registeredAddress" , "C" , "emailAddress" , "certificateTemplateName" ]
        
        self.site = site 
        self.company = company
        self.create_csr_and_private_key()
            

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
emailAddress 	= test@gmail.com
req_extensions	= v3_req
x509_extensions 	= v3_Ca
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn
utf8 = yes

[ dn ]
C= SA
OU= شركة اي تي سيستمتك
O= شركة اي تي سيستمتك
CN= ISb4102873-1982-4dc1-85f9-e95d86fb32ef

[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment

[req_ext]
certificateTemplateName = ASN1:PRINTABLESTRING:PREZATCA-Code-Signing
subjectAltName = dirName:alt_names


[alt_names]
SN = 1-ISb4102873-1uy|2-ISb4102873-1nt|3-ISb4102873-1pu
UID = 310094010300003
title = 1100
registeredAddress = it systematic-Billing
businessCategory = Commercial"""
        
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
    
    
    
    def make_process(self , command) :
        time.sleep(5)
        # subprocess.Popen(shlex.split(command), shell=False)
        subprocess.run(shlex.split(command), shell=False)
