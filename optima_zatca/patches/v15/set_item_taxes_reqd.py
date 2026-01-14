import click
from optima_zatca.setup.setup_vat_system.setup_item_tax_templates import setup_item_table_property_setter


def execute():
    """Patch to set 'item_tax_template' field as required in Item DocType."""
    click.secho("Executing patch: Set 'taxes' table in 'Item' DocType as required...", fg="cyan")
    setup_item_table_property_setter()
