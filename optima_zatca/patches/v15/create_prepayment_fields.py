"""
Create the Sales Invoice prepayment custom fields.

The field definitions now live in the single source of truth
(optima_zatca.setup.customizations); this patch just re-applies them so
already-installed sites pick them up. Patches run once, so schema changes to
these fields ship as NEW patches, not edits here.
"""

from click import secho

from optima_zatca.setup.customizations import ensure_customizations


def execute():
    secho("Create Prepayment Sales Invoice Fields Patch is running", fg="yellow")
    try:
        ensure_customizations()
        secho("Prepayment Sales Invoice custom fields added successfully", fg="green")
    except Exception as e:
        secho(f"Error adding Prepayment Sales Invoice custom fields: {str(e)}", fg="red")
