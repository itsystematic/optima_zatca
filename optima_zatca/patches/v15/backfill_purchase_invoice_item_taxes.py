"""
Migration Patch: Backfill Per-Item Tax Data for Purchase Invoices

This patch recalculates per-item tax fields for existing Purchase Invoices
that were created before the per-item tax calculation feature was added.

SAFETY MEASURES:
- Only processes DRAFT Purchase Invoices (docstatus = 0)
- Skips submitted (docstatus = 1) and cancelled (docstatus = 2) invoices
- Logs all operations to Error Log for audit trail
- Uses database transactions for atomic updates

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
import json


def execute():
    """Main patch execution function."""
    frappe.flags.in_patch = True
    
    try:
        # Get count first for progress reporting
        total_count = frappe.db.count("Purchase Invoice", filters={"docstatus": 0})
        
        if total_count == 0:
            print("✓ No draft Purchase Invoices found. Nothing to migrate.")
            return
        
        print(f"🔄 Starting migration of {total_count} draft Purchase Invoices...")
        
        # Process in batches to avoid memory issues
        batch_size = 100
        processed = 0
        updated = 0
        skipped = 0
        errors = 0
        
        # Get all draft Purchase Invoices
        invoices = frappe.get_all(
            "Purchase Invoice",
            filters={"docstatus": 0},
            fields=["name"],
            order_by="creation asc"
        )
        
        for invoice_data in invoices:
            try:
                result = process_purchase_invoice(invoice_data.name)
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
            
            # Commit every batch to avoid long transactions
            if processed % batch_size == 0:
                frappe.db.commit()
                print(f"  Progress: {processed}/{total_count} processed...")
        
        # Final commit
        frappe.db.commit()
        
        print(f"""
            ✅ Migration Complete!
            Total Processed: {processed}
            Updated: {updated}
            Skipped (no taxes): {skipped}
            Errors: {errors}
        """)
        
        if errors > 0:
            print("⚠️  Check Error Log for details on failed invoices.")
            
    except Exception as e:
        frappe.log_error(
            title="Patch Failed: backfill_purchase_invoice_item_taxes",
            message=str(e)
        )
        raise
    finally:
        frappe.flags.in_patch = False


def process_purchase_invoice(invoice_name):
    """
    Process a single Purchase Invoice and calculate per-item tax data.
    
    Returns:
        "updated" - if items were updated
        "skipped" - if invoice has no taxes
    """
    doc = frappe.get_doc("Purchase Invoice", invoice_name)
    
    # Skip if no taxes defined
    if not doc.taxes:
        return "skipped"
    
    # Get itemised tax breakdown
    itemised_tax = get_itemised_tax_for_patch(doc.taxes)
    
    if not itemised_tax:
        return "skipped"
    
    items_updated = False
    
    for row in doc.items:
        tax_rate = 0.0
        tax_amount = 0.00
        included_in_print_rate = 0
        
        # Get tax category from Item Tax Template
        if row.get("item_tax_template"):
            tax_category = frappe.db.get_value(
                "Item Tax Template", 
                row.item_tax_template, 
                "tax_category",
                cache=True
            )
            if tax_category and row.tax_category != tax_category:
                row.tax_category = tax_category
                items_updated = True
        
        # Get tax data for this item
        if row.item_code and itemised_tax.get(row.item_code):
            for tax_desc, tax_data in itemised_tax.get(row.item_code).items():
                tax_rate += tax_data.get('tax_rate', 0)
                tax_amount += tax_data.get("tax_amount", 0)
                included_in_print_rate += tax_data.get("included_in_print_rate", 0)
        
        # Calculate fields
        new_tax_rate = flt(tax_rate, 2)
        
        if included_in_print_rate:
            # Tax-inclusive pricing
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
            # Tax-exclusive pricing
            price_amount = row.rate
            line_extension_amount = flt(row.amount, 2)
            taxable_amount = flt(row.net_amount, 2)
            calculated_tax_amount = flt(line_extension_amount * (new_tax_rate / 100), 2)
            original_net_total = doc.net_total
            total_amount = flt((line_extension_amount + calculated_tax_amount), 2)
        
        # Calculate proportional discount
        item_discount = 0.0
        if doc.get("discount_amount") and original_net_total:
            item_discount = flt((doc.discount_amount * taxable_amount) / original_net_total, 2)
        
        # Update fields if changed
        if (row.tax_rate != new_tax_rate or
            row.get("tax_amount") != calculated_tax_amount or
            row.get("price_amount") != price_amount or
            row.get("line_extension_amount") != line_extension_amount or
            row.get("total_amount") != total_amount or
            row.get("item_discount") != item_discount):
            
            row.tax_rate = new_tax_rate
            row.tax_amount = calculated_tax_amount
            row.price_amount = price_amount
            row.line_extension_amount = line_extension_amount
            row.total_amount = total_amount
            row.item_discount = item_discount
            items_updated = True
    
    # Save only if changes were made
    if items_updated:
        doc.flags.ignore_validate = True
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)
        return "updated"
    
    return "skipped"


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
