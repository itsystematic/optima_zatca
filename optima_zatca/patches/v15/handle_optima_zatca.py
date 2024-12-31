import frappe
from click import secho
from optima_zatca.zatca.setup import saving_commercial_register
from optima_zatca.zatca.utils import extract_details_from_certificate , make_auth_header_for_request


def execute() :
    """ Handle Old Customer """
    print("Patches Runing")
    all_companies = get_all_companies()

    for company in all_companies :

        if not frappe.get_meta("Company").has_field("api_endpoints") :
            return 

        try :
            if company.api_endpoints != "production"  :
                return 

            commercial_register = create_commercial_register(company)
            create_optima_zatca_settings(company , commercial_register)
            handle_optima_logs(commercial_register)

            secho("Settings Created for Company => {} and commercial Register => {}".format(company.name , commercial_register) , fg="green")
        
        except Exception as e:
            secho("Error in Company => {}".format(company.name) , fg="red")
            print(e)



def get_all_companies() -> list[frappe._dict] :
    company = frappe.db.get_all("Company" , fields=["*"])
    return company


def create_commercial_register(company: frappe._dict) :
    
    commercial_register = saving_commercial_register( 
        company.name , company.registered_address ,
        commercial_register_name = company.organization_unit,
        commercial_register_number = company.get("commercial_register") or company.get("custom_commercial_register")
    )

    return commercial_register


def create_optima_zatca_settings(company , commercial_register):
    company_settings = {}
    optima_zatca_setting = frappe.new_doc("Optima Zatca Setting")

    optima_zatca_setting.company = company.name
    optima_zatca_setting.commercial_register = commercial_register
    optima_zatca_setting.address = company.registered_address
    optima_zatca_setting.phases = 'Phase 2'

    optima_zatca_setting.organization_identifier = company.tax_id
    optima_zatca_setting.organization_unit_name = company.organization_unit
    optima_zatca_setting.organization_name = company.custom_organization_name
    optima_zatca_setting.common_name = company.common_name
    optima_zatca_setting.egs_serial_number = company.sn
    optima_zatca_setting.registration_type = "CRN"
    optima_zatca_setting.country_name = "SA"
    optima_zatca_setting.industry = company.business_category
    optima_zatca_setting.invoice_type = company.title

    optima_zatca_setting.otp = company.otp
    optima_zatca_setting.api_endpoints = company.api_endpoints
    optima_zatca_setting.check_csr = 1
    optima_zatca_setting.check_csid = 1
    optima_zatca_setting.check_pcsid = 1
    optima_zatca_setting.invoice_one = 1
    optima_zatca_setting.invoice_two = 1
    optima_zatca_setting.invoice_three = 1
    optima_zatca_setting.invoice_four = 1
    optima_zatca_setting.invoice_five = 1
    optima_zatca_setting.invoice_six = 1
    optima_zatca_setting.private_key = company.pk 
    optima_zatca_setting.csr = company.csr
    optima_zatca_setting.request_id = company.csid 
    optima_zatca_setting.binary_security_token = company.binary_security_token
    optima_zatca_setting.certificate = company.certificate
    optima_zatca_setting.token_type = company.token_type
    optima_zatca_setting.secret = company.secret
    optima_zatca_setting.authorization = make_auth_header_for_request(company.binary_security_token , company.secret) 

    extract_details_from_certificate(company.certificate , company_settings)
    optima_zatca_setting.update(company_settings)

    optima_zatca_setting.save(ignore_permissions=True)


def handle_optima_logs(commercial_register):

    zatca_logs = frappe.get_all("Zatca Logs", fields=["*"], order_by="creation desc") 

    for log in zatca_logs :
        optima_zatca_logs = frappe.new_doc("Optima Zatca Logs")
        optima_zatca_logs.commercial_register = commercial_register
        optima_zatca_logs.environment = "production"
        optima_zatca_logs.api_endpoint = "complainace_checks" if log.endpoint == "complainace_checks" else "clearance"
        optima_zatca_logs.qr_code_generated = log.qr_code
        optima_zatca_logs.update(log)
        optima_zatca_logs.insert(ignore_permissions=True)

    frappe.db.commit()