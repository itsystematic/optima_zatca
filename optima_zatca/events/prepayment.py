import frappe
from frappe import _
from frappe.utils import flt
from optima_zatca.zatca.utils import log_and_throw_error


NORMAL_INVOICE_TYPE = "Normal"
INITIAL_PREPAYMENT_TYPE = "Initial Prepayment"
ADJUSTMENT_TYPES = ["Adjustment", "Final Adjustment"]
MIN_ADJUSTMENT_PERCENTAGE = 0
MAX_ADJUSTMENT_PERCENTAGE = 100
# Currency amounts compare at 2 dp; percentages at 9 dp so adjustment maths on
# repeating decimals isn't truncated (e.g. a max limit of 66.666666667%).
# Keep PERCENTAGE_PRECISION in sync with setup.customizations.PERCENTAGE_PRECISION
# and the field precision, and with toFixed() in public/js/sales_invoice.js.
PRECISION = 2
PERCENTAGE_PRECISION = 9


# ====================================================================================================
# ENTRY POINT
# Sales Invoice `validate` doc_event. Dispatches to the checks that apply to the invoice type;
# normal invoices short-circuit, adjustments run the full adjustment suite.


def validate_prepayments(doc, event):
    """Validate prepayment-related business rules for Sales Invoice"""
    try:
        if doc.sales_invoice_type == NORMAL_INVOICE_TYPE:
            return
        
        _validate_unique_initial_prepayment(doc) # No duplicate
        
        _validate_return_requirements(doc)
        
        # Additional validations only for adjustment invoices
        if doc.sales_invoice_type in ADJUSTMENT_TYPES:
            _validate_adjustment_requirements(doc)

    except frappe.ValidationError:
        # Expected business-rule rejection — surface the helper's specific
        # message as-is and keep it out of the Error Log.
        raise
    except Exception as e:
        # Only genuine, unexpected failures get logged + a friendly message.
        log_and_throw_error(
            operation="Validate Prepayment",
            document_name=doc.name or "New Document",
            exception=e
        )


# ====================================================================================================
# INITIAL PREPAYMENT UNIQUENESS
# A Sales Order may carry at most one Initial Prepayment invoice.


def _validate_unique_initial_prepayment(doc):
    """Validate that a Sales Order can only have one Initial Prepayment Sales Invoice"""

    if doc.sales_invoice_type != INITIAL_PREPAYMENT_TYPE:
        return
    
    if not doc.get("prepayment_sales_order"):
        return
    
    filters = {
        "prepayment_sales_order": doc.prepayment_sales_order,
        "sales_invoice_type": INITIAL_PREPAYMENT_TYPE,
        "docstatus": ["!=", 2]  # Not cancelled
    }
    
    # Exclude current document if it's being updated
    if not doc.is_new():
        filters["name"] = ["!=", doc.name]
    
    if existing_initial_prepayment := _get_existing_initial_prepayment(filters):
        frappe.throw(
            _("Sales Order {0} already has an Initial Prepayment Sales Invoice ({1}). Each Sales Order can only have one Initial Prepayment invoice.").format(
                frappe.bold(doc.prepayment_sales_order),
                frappe.bold(existing_initial_prepayment)
            ),
            title=_("Duplicate Initial Prepayment")
        )


def _get_existing_initial_prepayment(filters: dict) -> str:
    return frappe.db.get_value(
        "Sales Invoice",
        filters,
        "name"
    )


# ====================================================================================================
# RETURN & PREPAYMENT LINKAGE
# Return invoices must reference an existing, not-yet-linked Prepayment Invoice.


def _validate_return_requirements(doc):
    """Validate return invoice requirements"""
    if not doc.is_return:
        return
    
    if not doc.return_against:
        frappe.throw(_("Return Against is required for return invoices"))
    
    _validate_prepayment_linkage(doc)


def _validate_prepayment_linkage(doc):
    """Validate the referenced prepayment exists and is not linked to another Sales Invoice"""
    prepayment_data = frappe.db.get_value(
        "Prepayment Invoice", 
        doc.return_against, 
        ["is_linked", "name"],
        as_dict=True
    )

    if not prepayment_data:
        frappe.throw(
            _("Prepayment Invoice {0} does not exist").format(
                frappe.bold(doc.return_against)
            )
        )

    if prepayment_data.is_linked:
        frappe.throw(
            _("Prepayment Invoice {0} is already linked with another Sales Invoice").format(
                frappe.bold(doc.return_against)
            )
        )
        


# ====================================================================================================
# ADJUSTMENT VALIDATION
# Adjustment / Final Adjustment invoices: required fields, deducted-total ceilings, the
# adjustment-percentage range and its computed max limit, and POS vs non-POS payment ceilings.
# Currency compares at 2 dp; percentages at 9 dp (see PERCENTAGE_PRECISION note above).


def _validate_adjustment_requirements(doc):
    """Validate all adjustment-specific requirements"""
    _validate_required_fields(doc)
    _validate_deducted_totals(doc)
    _validate_pos_payment_for_adjustment(doc)
    _validate_adjustment_percentage_range(doc)
    _validate_adjustment_percentage_limit(doc)
    _validate_non_pos_payment_for_adjustment(doc)


def _validate_required_fields(doc):
    """Validate required fields for adjustment invoices"""
    required_fields = [
        ("adjustment_percentage", "Adjustment Percentage"),
        ("total_grands", "Total Grands"),
        ("grand_total", "Grand Total")
    ]
    
    for field, label in required_fields:
        if not doc.get(field):
            frappe.throw(_("{0} is required for adjustment invoices").format(_(label)))


def _validate_adjustment_percentage_range(doc):
    """Validate adjustment percentage is within valid range"""
    adjustment_percentage = flt(doc.adjustment_percentage, PERCENTAGE_PRECISION)
    
    if adjustment_percentage < MIN_ADJUSTMENT_PERCENTAGE or adjustment_percentage > MAX_ADJUSTMENT_PERCENTAGE:
        frappe.throw(
            _("Adjustment percentage must be between {0}% and {1}% (exclusive)").format(
                MIN_ADJUSTMENT_PERCENTAGE, MAX_ADJUSTMENT_PERCENTAGE
            )
        )


def _validate_deducted_totals(doc):
    """Validate deducted amounts are within acceptable limits"""
    deducted_total = flt(doc.get("deducted_grand_total"), PRECISION)
    # Use base_grand_total for multi-currency, fallback to grand_total for single currency
    grand_total = flt(doc.get("base_grand_total") or doc.get("grand_total"), PRECISION)
    
    # Use absolute values for comparison to handle negative invoices
    abs_deducted = abs(deducted_total)
    abs_grand = abs(grand_total)
    
    if abs_deducted > abs_grand:
        frappe.throw(
            _("Deducted Grand Total ({0}) cannot be greater than Grand Total ({1})").format(
                frappe.format_value(abs_deducted, {"fieldtype": "Currency"}),
                frappe.format_value(abs_grand, {"fieldtype": "Currency"})
            )
        )


def _validate_adjustment_percentage_limit(doc):
    """Validate adjustment percentage against calculated maximum limit"""

    total_grands = flt(doc.get("total_grands"), PRECISION)
    # Use base_grand_total for multi-currency, fallback to grand_total for single currency
    grand_total = flt(doc.get("base_grand_total") or doc.get("grand_total"), PRECISION)
    adjustment_percentage = flt(doc.get("adjustment_percentage"), PERCENTAGE_PRECISION)

    if total_grands == 0:
        frappe.throw(_("Total Grands cannot be zero for adjustment percentage calculation"))
    
    max_adjustment_limit = _calculate_max_adjustment_limit(grand_total, total_grands)
    
    if adjustment_percentage > max_adjustment_limit:
        frappe.throw(
            _("Adjustment percentage ({0}%) cannot exceed the maximum limit of {1}%").format(
                frappe.format_value(adjustment_percentage, {"fieldtype": "Percent"}),
                frappe.format_value(max_adjustment_limit, {"fieldtype": "Percent"})
            )
        )


def _calculate_max_adjustment_limit(grand_total, total_grands):
    """Calculate maximum adjustment percentage limit"""
    abs_grand_total = abs(flt(grand_total, PRECISION))
    abs_total_grands = abs(flt(total_grands, PRECISION))
    
    if abs_total_grands == 0:
        return 0
    
    max_limit = (abs_grand_total * 100) / abs_total_grands
    return flt(max_limit, PERCENTAGE_PRECISION)


def _validate_pos_payment_for_adjustment(doc):
    """Validate POS payment requirements for adjustment invoices"""
    if doc.get("is_pos") != 1:
        return
    
    deducted_grand_total = flt(doc.get("deducted_grand_total"), PRECISION)
    paid_amount = flt(doc.get("paid_amount"), PRECISION)
    # Use base_grand_total for multi-currency, fallback to grand_total for single currency
    grand_total = flt(doc.get("base_grand_total") or doc.get("grand_total"), PRECISION)
    
    # Use absolute values for comparison to handle negative invoices
    abs_deducted = abs(deducted_grand_total)
    abs_paid = abs(paid_amount)
    abs_grand = abs(grand_total)
    
    if abs_deducted + abs_paid > abs_grand:
        frappe.throw(
            _("(Deducted Grand Total + Paid Amount) Must Be Less Than Or Equal To The Grand Total")
        )


def _validate_non_pos_payment_for_adjustment(doc):
    """Validate non-POS payment requirements for adjustment invoices"""
    if doc.get("is_pos") != 0:
        return
    
    deducted_grand_total = flt(doc.get("deducted_grand_total"), PRECISION)
    total_advance = flt(doc.get("total_advance"), PRECISION)
    # Use base_grand_total for multi-currency, fallback to grand_total for single currency
    grand_total = flt(doc.get("base_grand_total") or doc.get("grand_total"), PRECISION)
    
    # Use absolute values for comparison to handle negative invoices
    abs_deducted = abs(deducted_grand_total)
    abs_total_advance = abs(total_advance)
    abs_grand = abs(grand_total)
    
    if abs_deducted + abs_total_advance > abs_grand:
        frappe.throw(
            _("Deducted Grand Total + Total Advance Must Be Less Than Or Equal To The Grand Total")
        )

