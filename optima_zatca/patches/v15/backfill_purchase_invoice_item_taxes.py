"""
Migration Patch: Backfill Per-Item Tax Data for Purchase Invoices

This patch recalculates per-item tax fields for existing Purchase Invoices
that were created before the per-item tax calculation feature was added.

SAFETY MEASURES:
- Processes both draft (docstatus=0) and submitted (docstatus=1) invoices
- Skips cancelled invoices (docstatus=2)
- Draft invoices: updated via doc.save() with ignore_validate
- Submitted invoices: updated via direct DB writes (frappe.db.set_value)
  to avoid triggering validation on old documents
- update_modified=False preserves audit timestamps on submitted docs
- Only writes custom display fields — no financial fields or GL entries are touched
- Idempotent: checks if values differ before writing
- Batched commits every 100 invoices

Custom fields populated:
- tax_category: Tax category from Item Tax Template
- price_amount: Unit price before tax
- line_extension_amount: Net taxable amount per line
- item_discount: Proportional discount per item
- tax_rate: Combined tax rate (%)
- tax_amount: Tax amount per line
- total_amount: Line total including tax
"""

import frappe
from frappe.utils import flt
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
import json


REQUIRED_FIELDS = {
    "Purchase Invoice Item": [
        {
            "fieldname": "tax_category",
            "fieldtype": "Link",
            "label": "Tax Category",
            "insert_after": "item_tax_template",
            "options": "Tax Category",
            "read_only": 1,
            "hidden": 1,
        },
        {
            "fieldname": "price_amount",
            "label": "Price Amount",
            "fieldtype": "Float",
            "insert_after": "tax_category",
            "read_only": 1,
            "hidden": 1,
            "no_copy": 1,
        },
        {
            "fieldname": "line_extension_amount",
            "label": "Line Extension Amount",
            "fieldtype": "Float",
            "insert_after": "price_amount",
            "read_only": 1,
            "hidden": 1,
            "no_copy": 1,
        },
        {
            "fieldname": "item_discount",
            "label": "Item Discount",
            "fieldtype": "Float",
            "insert_after": "line_extension_amount",
            "read_only": 1,
            "hidden": 1,
            "no_copy": 1,
        },
    ]
}


def ensure_custom_fields():
    """Create any missing custom fields on Purchase Invoice Item."""
    create_custom_fields(REQUIRED_FIELDS, update=True)
    frappe.db.commit()
    # Clear cache so frappe.get_doc picks up new columns
    frappe.clear_cache(doctype="Purchase Invoice")


def execute():
    """Main patch execution function."""
    frappe.flags.in_patch = True

    ensure_custom_fields()

    try:
        total_count = frappe.db.count(
            "Purchase Invoice", filters={"docstatus": ["in", [0, 1]]}
        )

        if total_count == 0:
            print("No draft or submitted Purchase Invoices found. Nothing to migrate.")
            return

        print(f"Starting migration of {total_count} Purchase Invoices (drafts + submitted)...")

        batch_size = 100
        processed = 0
        updated = 0
        skipped = 0
        errors = 0

        invoices = frappe.get_all(
            "Purchase Invoice",
            filters={"docstatus": ["in", [0, 1]]},
            fields=["name", "docstatus"],
            order_by="creation asc"
        )

        for invoice_data in invoices:
            try:
                result = process_purchase_invoice(
                    invoice_data.name, invoice_data.docstatus
                )
                if result == "updated":
                    updated += 1
                elif result == "skipped":
                    skipped += 1
            except Exception as e:
                errors += 1
                frappe.log_error(
                    title=f"Patch Error: Purchase Invoice {invoice_data.name}",
                    message=str(e)
                )

            processed += 1

            if processed % batch_size == 0:
                frappe.db.commit()
                print(f"  Progress: {processed}/{total_count} processed...")

        frappe.db.commit()

        summary = (
            f"\nMigration Complete!\n"
            f"  Total Processed: {processed}\n"
            f"  Updated: {updated}\n"
            f"  Skipped (no taxes): {skipped}\n"
            f"  Errors: {errors}"
        )
        print(summary)

        if errors > 0:
            print("Check Error Log for details on failed invoices.")

    except Exception as e:
        frappe.log_error(
            title="Patch Failed: backfill_purchase_invoice_item_taxes",
            message=str(e)
        )
        raise
    finally:
        frappe.flags.in_patch = False


def process_purchase_invoice(invoice_name, docstatus):
    """
    Process a single Purchase Invoice and calculate per-item tax data.

    Args:
        invoice_name: Purchase Invoice name
        docstatus: 0 for draft, 1 for submitted

    Returns:
        "updated" - if items were updated
        "skipped" - if invoice has no taxes or no changes needed
    """
    doc = frappe.get_doc("Purchase Invoice", invoice_name)

    if not doc.taxes:
        return "skipped"

    itemised_tax = get_itemised_tax_for_patch(doc.taxes)

    if not itemised_tax:
        return "skipped"

    items_updated = False

    for row in doc.items:
        tax_rate = 0.0
        tax_amount = 0.00
        included_in_print_rate = 0

        # Get tax category from Item Tax Template
        tax_category = None
        if row.get("item_tax_template"):
            tax_category = frappe.db.get_value(
                "Item Tax Template",
                row.item_tax_template,
                "tax_category",
                cache=True
            )

        # Get tax data for this item
        if row.item_code and itemised_tax.get(row.item_code):
            for tax_desc, tax_data in itemised_tax.get(row.item_code).items():
                tax_rate += tax_data.get("tax_rate", 0)
                tax_amount += tax_data.get("tax_amount", 0)
                included_in_print_rate += tax_data.get("included_in_print_rate", 0)

        new_tax_rate = flt(tax_rate, 2)

        if included_in_print_rate:
            if new_tax_rate > 0:
                line_extension_amount = flt(row.amount / ((new_tax_rate / 100) + 1), 2)
            else:
                line_extension_amount = flt(row.amount, 2)
            taxable_amount = line_extension_amount
            qty = flt(row.get("qty") or 0)
            price_amount = flt(taxable_amount / qty, 2) if qty != 0 else 0.0
            calculated_tax_amount = flt(row.amount - taxable_amount, 2)
            original_net_total = doc.net_total + (doc.get("discount_amount", 0.00) or 0.00)
            total_amount = row.amount
        else:
            price_amount = row.rate
            line_extension_amount = flt(row.amount, 2)
            taxable_amount = flt(row.net_amount, 2)
            calculated_tax_amount = flt(line_extension_amount * (new_tax_rate / 100), 2)
            original_net_total = doc.net_total
            total_amount = flt((line_extension_amount + calculated_tax_amount), 2)

        # Calculate proportional discount (guard against zero net_total)
        item_discount = 0.0
        if doc.get("discount_amount") and original_net_total and original_net_total != 0:
            item_discount = flt(
                (doc.discount_amount * taxable_amount) / original_net_total, 2
            )

        # Build the update dict for this row
        new_values = {
            "tax_category": tax_category or "",
            "price_amount": price_amount,
            "line_extension_amount": line_extension_amount,
            "item_discount": item_discount,
            "tax_rate": new_tax_rate,
            "tax_amount": calculated_tax_amount,
            "total_amount": total_amount,
        }

        # Check if any value actually changed
        row_changed = False
        for field, new_val in new_values.items():
            current_val = row.get(field)
            if field == "tax_category":
                if (current_val or "") != (new_val or ""):
                    row_changed = True
                    break
            else:
                if flt(current_val, 2) != flt(new_val, 2):
                    row_changed = True
                    break

        if row_changed:
            items_updated = True
            if docstatus == 1:
                # Submitted invoice: direct DB write on child row, no validation triggered
                frappe.db.set_value(
                    "Purchase Invoice Item",
                    row.name,
                    new_values,
                    update_modified=False,
                )
            else:
                # Draft invoice: set in-memory values for doc.save() below
                for field, new_val in new_values.items():
                    setattr(row, field, new_val)

    if not items_updated:
        return "skipped"

    if docstatus == 0:
        doc.flags.ignore_validate = True
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)

    return "updated"


def get_itemised_tax_for_patch(taxes):
    """
    Extract per-item tax data from the taxes table.
    This is a standalone version for the patch to avoid import dependencies.
    """
    itemised_tax = {}
    
    for tax in taxes:
        if getattr(tax, "category", None) and tax.category == "Valuation":
            continue
        
        item_tax_map = {}
        if tax.item_wise_tax_detail:
            try:
                item_tax_map = json.loads(tax.item_wise_tax_detail)
            except (json.JSONDecodeError, TypeError):
                continue
        
        if item_tax_map:
            for item_code, tax_data in item_tax_map.items():
                itemised_tax.setdefault(item_code, frappe._dict())
                
                tax_rate = 0.0
                tax_amount = 0.0
                
                if isinstance(tax_data, list):
                    tax_rate = flt(tax_data[0])
                    tax_amount = flt(tax_data[1])
                else:
                    tax_rate = flt(tax_data)
                
                itemised_tax[item_code][tax.description] = frappe._dict(
                    tax_rate=tax_rate,
                    tax_amount=tax_amount,
                    included_in_print_rate=tax.included_in_print_rate,
                    tax_account=tax.account_head
                )
    
    return itemised_tax
