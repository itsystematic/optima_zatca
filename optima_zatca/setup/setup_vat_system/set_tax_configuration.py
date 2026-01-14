import click

from optima_zatca.setup.setup_vat_system.setup_item_tax_templates import (
    create_item_tax_templates,
    setup_item_table_property_setter
)
from optima_zatca.setup.setup_vat_system.setup_tax_accounts import create_tax_accounts
from optima_zatca.setup.setup_vat_system.setup_tax_cateogries import create_tax_categories



def create_complete_vat_system():
    """
    Complete VAT system setup for KSA - run everything in sequence
    Can be called from install, patches, or manuall
    """
    click.secho("Setting up complete KSA VAT system...", fg="magenta", bold=True)
    
    try:
        # Step 1: Create Tax Categories (S, Z, E, O)
        create_tax_categories()
        
        # Step 2: Create Tax Accounts (Assets & Liabilities)
        create_tax_accounts()
        
        # Step 3: Create Item Tax Templates (8 templates)
        create_item_tax_templates()
        
        # Step 4: Set Item taxes table as required In Item DocType
        setup_item_table_property_setter()
        
        click.secho("\nKSA VAT SYSTEM SETUP COMPLETE!", fg="green", bold=True)
        click.secho("Tax Categories: S, Z, E, O", fg="green")
        click.secho("Tax Accounts: Organized under Assets/Liabilities", fg="green") 
        click.secho("Item Tax Templates: 8 templates ready", fg="green")
        
        click.secho("\nTemplates Created:", fg="cyan", bold=True)
        click.secho("SELLING: KSA VAT [15%|0%|Exempt|Out of Scope] Selling", fg="blue")
        click.secho("BUYING: KSA VAT [15%|0%|Exempt|Out of Scope] Buying", fg="blue")
        
        click.secho("\nKSA VAT system is ready to use!", fg="green", bold=True)
        click.secho("Assign these templates to your items and start invoicing.", fg="blue")
        
    except Exception as e:
        click.secho(f"\nSetup failed: {str(e)}", fg="red", bold=True)
        raise