import click
import frappe


TAX_CATEGORIES = [
    "S", "Z", "E", "O",
    "S - Buying", "Z - Buying", "E - Buying", "O - Buying",
]


def create_tax_categories():
    """
    Create tax categories if they don't exist.
    Avoids duplicates and provides detailed feedback.
    """
    click.secho(" Creating tax categories...", fg="cyan")
    
    created_count = 0
    existing_count = 0
    
    for category_name in TAX_CATEGORIES:
        if frappe.db.exists("Tax Category", category_name):
            click.secho(f"    Tax category '{category_name}' already exists", fg="yellow")
            existing_count += 1
        else:
            try:
                tax_category = frappe.new_doc("Tax Category")
                tax_category.name = category_name
                tax_category.title = category_name

                tax_category.insert(ignore_permissions=True)
                
                click.secho(f"  Created tax category '{category_name}'", fg="green")
                created_count += 1
                
            except Exception as e:
                click.secho(f"  Failed to create '{category_name}': {str(e)}", fg="red")
                raise
    
    # Summary
    total = len(TAX_CATEGORIES)
    click.secho(
        f" Tax categories summary: {created_count} created, {existing_count} existing, {total} total", 
        fg="blue"
    )