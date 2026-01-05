import frappe
import click

TAX_CATEGORIES = ["S - Buying", "Z - Buying", "E - Buying", "O - Buying"]

TAX_ACCOUNTS_CONFIG = {
    "sales": {
        "parent_search": "Duties and Taxes",  # Under Current Liabilities
        "fallback_path": ["Liabilities", "Current Liabilities"],
        "accounts": [
            {"name": "Output VAT 15%", "rate": 15, "category": "S"},
            {"name": "Output VAT 0%", "rate": 0, "category": "Z"}, 
            {"name": "VAT Exempt - Sales", "rate": 0, "category": "E"},
            {"name": "Out of Scope - Sales", "rate": 0, "category": "O"}
        ]
    },
    "purchases": {
        "parent_search": "Tax Assets",  # Under Current Assets  
        "fallback_path": ["Assets", "Current Assets"],
        "accounts": [
            {"name": "Input VAT 15%", "rate": 15, "category": "S"},
            {"name": "Input VAT 0%", "rate": 0, "category": "Z"},
            {"name": "VAT Exempt - Purchases", "rate": 0, "category": "E"}, 
            {"name": "Out of Scope - Purchases", "rate": 0, "category": "O"}
        ]
    }
}


def set_tax_configuration():
    """
    Main function to set up all tax configuration.
    Can be called from install, patches, or manually.
    """
    click.secho("🔧 Setting up tax configuration...", fg="yellow")
    
    try:
        create_tax_categories()
        click.secho("✅ Tax configuration completed successfully!", fg="green")
    except Exception as e:
        click.secho(f"❌ Error in tax configuration: {str(e)}", fg="red")
        raise


def create_tax_categories():
    """
    Create tax categories if they don't exist.
    Avoids duplicates and provides detailed feedback.
    """
    click.secho("📋 Creating tax categories...", fg="cyan")
    
    created_count = 0
    existing_count = 0
    
    for category_name in TAX_CATEGORIES:
        if frappe.db.exists("Tax Category", category_name):
            click.secho(f"  ⚠️  Tax category '{category_name}' already exists", fg="yellow")
            existing_count += 1
        else:
            try:
                tax_category = frappe.new_doc("Tax Category")
                tax_category.name = category_name
                tax_category.title = category_name

                tax_category.insert(ignore_permissions=True)
                
                click.secho(f"  ✅ Created tax category '{category_name}'", fg="green")
                created_count += 1
                
            except Exception as e:
                click.secho(f"  ❌ Failed to create '{category_name}': {str(e)}", fg="red")
                raise
    
    # Summary
    total = len(TAX_CATEGORIES)
    click.secho(
        f"📊 Tax categories summary: {created_count} created, {existing_count} existing, {total} total", 
        fg="blue"
    )


def create_tax_accounts():
    """Create tax accounts in proper accounting locations"""
    click.secho("💰 Creating tax accounts...", fg="cyan")
    
    companies = frappe.get_all("Company", fields=["name", "abbr"])
    
    for company in companies:
        click.secho(f"  📊 Setting up tax accounts for {company.name}...", fg="blue")
        
        # Create sales accounts (under Liabilities)
        sales_parent = get_or_create_duties_and_taxes_parent(company.name, company.abbr)
        create_accounts_for_type(company, sales_parent, "sales", TAX_ACCOUNTS_CONFIG["sales"])
        
        # Create purchase accounts (under Assets)  
        purchase_parent = get_or_create_tax_assets_parent(company.name, company.abbr)
        create_accounts_for_type(company, purchase_parent, "purchases", TAX_ACCOUNTS_CONFIG["purchases"])


def get_or_create_duties_and_taxes_parent(company_name, company_abbr):
    """Get or create Duties and Taxes under Current Liabilities"""
    duties_taxes_name = f"Duties and Taxes - {company_abbr}"
    
    if frappe.db.exists("Account", duties_taxes_name):
        click.secho(f"    🎯 Using existing Duties and Taxes", fg="blue")
        return duties_taxes_name
    
    # Find Current Liabilities (bulletproof - always exists)
    current_liabilities_name = f"Current Liabilities - {company_abbr}"
    
    if not frappe.db.exists("Account", current_liabilities_name):
        # Fallback to any Liability group account
        liability_accounts = frappe.get_list(
            "Account",
            filters={
                "company": company_name,
                "root_type": "Liability", 
                "is_group": 1
            },
            fields=["name"],
            limit=1
        )
        parent_account = liability_accounts[0].name if liability_accounts else None
    else:
        parent_account = current_liabilities_name
    
    if not parent_account:
        frappe.throw(f"No Liability accounts found for {company_name}")
    
    # Create Duties and Taxes
    click.secho(f"    🏗️ Creating Duties and Taxes under {parent_account}", fg="yellow")
    
    duties_taxes = frappe.new_doc("Account")
    duties_taxes.account_name = "Duties and Taxes"
    duties_taxes.parent_account = parent_account
    duties_taxes.company = company_name
    duties_taxes.account_type = "Tax"
    duties_taxes.root_type = "Liability"
    duties_taxes.is_group = 1
    duties_taxes.insert(ignore_permissions=True)
    
    click.secho(f"    ✅ Created: {duties_taxes_name}", fg="green")
    return duties_taxes_name


def get_or_create_tax_assets_parent(company_name, company_abbr):
    """Get or create Tax Assets under Current Assets (same as before)"""
    tax_assets_name = f"Tax Assets - {company_abbr}"
    
    if frappe.db.exists("Account", tax_assets_name):
        click.secho(f"    🎯 Using existing Tax Assets", fg="blue")
        return tax_assets_name
    
    # Find Current Assets (bulletproof)
    current_assets_name = f"Current Assets - {company_abbr}"
    
    if not frappe.db.exists("Account", current_assets_name):
        asset_accounts = frappe.get_list(
            "Account",
            filters={
                "company": company_name,
                "root_type": "Asset",
                "is_group": 1
            },
            fields=["name"], 
            limit=1
        )
        parent_account = asset_accounts[0].name if asset_accounts else None
    else:
        parent_account = current_assets_name
    
    # Create Tax Assets
    click.secho(f"    🏗️ Creating Tax Assets under {parent_account}", fg="yellow")
    
    tax_assets = frappe.new_doc("Account")
    tax_assets.account_name = "Tax Assets"
    tax_assets.parent_account = parent_account
    tax_assets.company = company_name
    tax_assets.account_type = "Tax"
    tax_assets.root_type = "Asset"
    tax_assets.is_group = 1
    tax_assets.insert(ignore_permissions=True)
    
    click.secho(f"    ✅ Created: {tax_assets_name}", fg="green")
    return tax_assets_name


def create_accounts_for_type(company, parent_account, account_type, config):
    """Create individual tax accounts"""
    for account_info in config["accounts"]:
        account_name = f"{account_info['name']} - {company.abbr}"
        
        if frappe.db.exists("Account", account_name):
            click.secho(f"    ⚠️  Account '{account_name}' already exists", fg="yellow")
        else:
            try:
                account = frappe.new_doc("Account")
                account.account_name = account_info["name"]
                account.parent_account = parent_account
                account.company = company.name
                account.account_type = "Tax"
                account.root_type = "Liability" if account_type == "sales" else "Asset"
                account.is_group = 0
                account.insert(ignore_permissions=True)
                
                click.secho(f"    ✅ Created '{account_name}'", fg="green")
                
            except Exception as e:
                click.secho(f"    ❌ Failed to create '{account_name}': {str(e)}", fg="red")
                raise