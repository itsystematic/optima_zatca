import click
import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter



ITEM_TAX_TEMPLATES_CONFIG = [
    # SELLING Templates (Output VAT - Liabilities)
    {
        "title": "KSA VAT 15% Selling",
        "tax_category": "S",  # Links to our Standard Rate category
        "account_name": "Output VAT 15%",
        "tax_rate": 15.0,
    },
    {
        "title": "KSA VAT 0% Selling",
        "tax_category": "Z",  
        "account_name": "Output VAT 0%",
        "tax_rate": 0.0,
    },
    {
        "title": "KSA VAT Exempt Selling",
        "tax_category": "E",
        "account_name": "VAT Exempt - Sales",
        "tax_rate": 0.0,
    },
    {
        "title": "KSA VAT Out of Scope Selling",
        "tax_category": "O",
        "account_name": "Out of Scope - Sales", 
        "tax_rate": 0.0,
    },
    
    # BUYING Templates (Input VAT - Assets)
    {
        "title": "KSA VAT 15% Buying",
        "tax_category": "S - Buying",  # Links to our Standard Rate category
        "account_name": "Input VAT 15%",
        "tax_rate": 15.0,
    },
    {
        "title": "KSA VAT 0% Buying", 
        "tax_category": "Z - Buying",
        "account_name": "Input VAT 0%",
        "tax_rate": 0.0,
    },
    {
        "title": "KSA VAT Exempt Buying",
        "tax_category": "E - Buying",
        "account_name": "VAT Exempt - Purchases",
        "tax_rate": 0.0,
    },
    {
        "title": "KSA VAT Out of Scope Buying",
        "tax_category": "O - Buying",
        "account_name": "Out of Scope - Purchases",
        "tax_rate": 0.0,
    }
]

def create_item_tax_templates():
    """Create Item Tax Templates for KSA"""
    click.secho("Creating Item Tax Templates...", fg="cyan")
    
    companies = frappe.get_all("Company", fields=["name", "abbr"])
    
    for company in companies:        
        for template_config in ITEM_TAX_TEMPLATES_CONFIG:
            create_single_tax_template(company, template_config)
        
        click.secho(f"  Completed templates for {company.name}", fg="green")


def create_single_tax_template(company, template_config):
    """Create individual Item Tax Template following KSA structure"""

    template_name = f"{template_config['title']} - {company.abbr}"
    account_name = f"{template_config['account_name']} - {company.abbr}"
    
    if frappe.db.exists("Item Tax Template", template_name):
        click.secho(f"    ⚠️ Itme Tax Template '{template_name}' already exists!", fg="yellow")
        return
    
    # Verify the tax account exists
    if not frappe.db.exists("Account", account_name):
        click.secho(f"    Tax account '{account_name}' not found! Skipping template.", fg="red")
        return
    
    # Verify the tax category exists  
    if not frappe.db.exists("Tax Category", template_config["tax_category"]):
        click.secho(f"    Tax category '{template_config['tax_category']}' not found! Skipping template.", fg="red")
        return
    
    try:
        tax_template = frappe.new_doc("Item Tax Template")
        tax_template.title = template_config["title"]  # "KSA VAT 15% Selling"
        tax_template.company = company.name
        tax_template.tax_category = template_config["tax_category"]  # S, Z, E, or O
        
        tax_template.append("taxes", {
            "tax_type": account_name,  # Links to our tax account
            "tax_rate": template_config["tax_rate"]  # 15, 0, 0, 0
        })
        
        tax_template.insert(ignore_permissions=True)
        
        click.secho(f"    Created '{template_name}'", fg="green")
        click.secho(f"        Category: {template_config['tax_category']}", fg="blue") 
        click.secho(f"        Account: {account_name}", fg="blue")
        click.secho(f"        Rate: {template_config['tax_rate']}%", fg="blue")
        
    except Exception as e:
        click.secho(f"    Failed to create '{template_name}': {str(e)}", fg="red")
        raise


def setup_item_table_property_setter():
    """
    Set 'taxes' table in 'Item' DocType as required.
    """
    click.secho("Setting Item taxes table as required...", fg="cyan")
    make_property_setter(
        "Item",
        "taxes",
        "reqd",
        "1",
        "Check",
        for_doctype=False,
        is_system_generated=False
    )
    click.secho("Property Setter for Item taxes created/updated.", fg="green")