import io
import os
import frappe
from frappe import _
from base64 import b64encode
from erpnext import get_region
from pyqrcode import create as qr_create
from frappe.utils import getdate , get_time , add_to_date, flt
from optima_zatca.zatca.utils import log_and_throw_error


def sales_invoice_before_cancel(doc , event) :

    enable_cancel_invoice = frappe.db.get_single_value("Zatca Main Settings" , "enable_cancel_invoice")
    
    if doc.get("sent_to_zatca") and doc.get("clearance_or_reporting") in ["CLEARED" , "REPORTED"] and not enable_cancel_invoice :
        frappe.throw(_("No Permission To Cancel Invoice Sent To Zatca") , title=_("Zatca Permission"))


def sales_invoice_on_trash(doc , event) :

    enable_delete_invoice = frappe.db.get_single_value("Zatca Main Settings" , "enable_delete_invoice")

    if doc.get("sent_to_zatca") and doc.get("clearance_or_reporting") in ["CLEARED" , "REPORTED"] and not enable_delete_invoice :
        frappe.throw(_("No Permission To Delete Invoice Sent To Zatca") , title=_("Zatca Permission"))



def sales_invoice_on_submit(doc , event) :

    # Check if Phase One is disabled and handle conditions
    if frappe.db.get_single_value("Zatca Main Settings", "phase") != "Phase One":
        if doc.get("sent_to_zatca") == 1:
            return
        if doc.clearance_or_reporting not in ["REPORTED", "CLEARED"]:
            frappe.throw(_("Invoice Not Reported Yet"), title=_("Zatca Error"))

    # Validate Saudi Arabia region
    if get_region(doc.company) != 'Saudi Arabia':
        return

    # Skip if QR code already exists
    if doc.ksa_einv_qr and frappe.db.exists("File", {"file_url": doc.ksa_einv_qr}):
        return

    tlv_array = []
    # Sellers Name

    seller_name = frappe.db.get_value('Company',doc.company,'company_name_in_arabic')

    if not seller_name:
        frappe.throw(_('Arabic name missing for {} in the company document').format(doc.company))

    tag = bytes([1]).hex()
    length = bytes([len(seller_name.encode('utf-8'))]).hex()
    value = seller_name.encode('utf-8').hex()
    tlv_array.append(''.join([tag, length, value]))

    # VAT Number
    tax_id = frappe.db.get_value('Company', doc.company, 'tax_id')
    if not tax_id:
        frappe.throw(_('Tax ID missing for {} in the company document').format(doc.company))

    tag = bytes([2]).hex()
    length = bytes([len(tax_id)]).hex()
    value = tax_id.encode('utf-8').hex()
    tlv_array.append(''.join([tag, length, value]))

    # Time Stamp
    posting_date = getdate(doc.posting_date)
    time = get_time(doc.posting_time)
    seconds = time.hour * 60 * 60 + time.minute * 60 + time.second
    time_stamp = add_to_date(posting_date, seconds=seconds)
    time_stamp = time_stamp.strftime('%Y-%m-%dT%H:%M:%SZ')

    tag = bytes([3]).hex()
    length = bytes([len(time_stamp)]).hex()
    value = time_stamp.encode('utf-8').hex()
    tlv_array.append(''.join([tag, length, value]))

    # Invoice Amount
    invoice_amount = str(doc.grand_total)
    tag = bytes([4]).hex()
    length = bytes([len(invoice_amount)]).hex()
    value = invoice_amount.encode('utf-8').hex()
    tlv_array.append(''.join([tag, length, value]))

    # VAT Amount
    total_vat_amount = 0
    taxes_rate = []
    accounts_type_tax = frappe.get_list("Item Tax Template" , {"company" : doc.company , "disabled" : 0} ,['`tabItem Tax Template Detail`.tax_type'] , join="Left join")
    tax_accounts = list(map(lambda x : x.get("tax_type") , accounts_type_tax))
    vat_amount_row  = list(filter(lambda x : x.get("account_head") in tax_accounts , doc.taxes))
    
    for tax in vat_amount_row :
        
        if tax.get("rate")  in taxes_rate :
            frappe.throw(_("VAT {} is Duplicated in Document {}").format(tax.get("rate"),doc.name))
        total_vat_amount += tax.get("tax_amount")
        taxes_rate.append(tax.get("rate"))
        
    vat_amount = str(total_vat_amount)
    tag = bytes([5]).hex()
    length = bytes([len((vat_amount))]).hex()
    value = vat_amount.encode('utf-8').hex()
    tlv_array.append(''.join([tag, length, value]))

    # Joining bytes into one
    tlv_buff = ''.join(tlv_array)

    # base64 conversion for QR Code
    base64_string = b64encode(bytes.fromhex(tlv_buff)).decode()

    qr_image = io.BytesIO()
    url = qr_create(base64_string, error='L')
    url.png(qr_image, scale=2, quiet_zone=1)

    name = frappe.generate_hash(doc.name, 5)

    # making file
    filename = f"QRCode-{name}.png".replace(os.path.sep, "__")
    _file = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "is_private": 0,
        "content": qr_image.getvalue(),
        "attached_to_doctype": doc.get("doctype"),
        "attached_to_name": doc.get("name"),
        "attached_to_field": "ksa_einv_qr"
    })

    _file.save()

    # assigning to document
    doc.db_set('ksa_einv_qr', _file.file_url)
    doc.notify_update()


NORMAL_INVOICE_TYPE = "Normal"
ADJUSTMENT_TYPES = ["Adjustment", "Final Adjustment"]
MIN_ADJUSTMENT_PERCENTAGE = 0
MAX_ADJUSTMENT_PERCENTAGE = 100
PRECISION = 2

def validate_prepayments(doc, event):
    """Validate prepayment-related business rules for Sales Invoice"""
    try:
        # Validate Sales Order doesn't have duplicate Initial Prepayment
        _validate_unique_initial_prepayment(doc)
        
        # Early return for normal invoices
        if doc.sales_invoice_type == NORMAL_INVOICE_TYPE:
            return
            
        # Validate return requirements for all non-normal invoices
        _validate_return_requirements(doc)
        
        # Additional validations only for adjustment invoices
        if doc.sales_invoice_type in ADJUSTMENT_TYPES:
            _validate_adjustment_requirements(doc)
        
    except Exception as e:
        log_and_throw_error(
            operation="Validate Prepayment", 
            document_name=doc.name or "New Document", 
            exception=e
        )


def _validate_unique_initial_prepayment(doc):
    """Validate that a Sales Order can only have one Initial Prepayment Sales Invoice"""
    # Only check for Initial Prepayment invoices
    if doc.sales_invoice_type != "Initial Prepayment":
        return
    
    # Only check if prepayment_sales_order is set
    if not doc.get("prepayment_sales_order"):
        return
    
    # Check if another Initial Prepayment already exists for this Sales Order
    filters = {
        "prepayment_sales_order": doc.prepayment_sales_order,
        "sales_invoice_type": "Initial Prepayment",
        "docstatus": ["!=", 2]  # Not cancelled
    }
    
    # Exclude current document if it's being updated
    if not doc.is_new():
        filters["name"] = ["!=", doc.name]
    
    existing_initial_prepayment = frappe.db.get_value(
        "Sales Invoice",
        filters,
        "name"
    )
    
    if existing_initial_prepayment:
        frappe.throw(
            _("Sales Order {0} already has an Initial Prepayment Sales Invoice ({1}). Each Sales Order can only have one Initial Prepayment invoice.").format(
                frappe.bold(doc.prepayment_sales_order),
                frappe.bold(existing_initial_prepayment)
            ),
            title=_("Duplicate Initial Prepayment")
        )




def _validate_return_requirements(doc):
    """Validate return invoice requirements"""
    if not doc.is_return:
        return
    
    # Check return_against is provided
    if not doc.return_against:
        frappe.throw(_("Return Against is required for return invoices"))
    
    # Validate the referenced prepayment exists and is not linked
    _validate_prepayment_linkage(doc)


def _validate_prepayment_linkage(doc):
    """Validate prepayment invoice linkage status"""
    try:
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
            
    except frappe.DoesNotExistError:
        frappe.throw(
            _("Prepayment Invoice {0} does not exist").format(
                frappe.bold(doc.return_against)
            )
        )


def _validate_adjustment_requirements(doc):
    """Validate all adjustment-specific requirements"""
    _validate_adjustment_percentage_range(doc)
    _validate_required_fields(doc)
    _validate_deducted_totals(doc)
    _validate_adjustment_percentage_limit(doc)
    _validate_pos_payment_for_adjustment(doc)
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
    adjustment_percentage = flt(doc.adjustment_percentage, PRECISION)
    
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
    adjustment_percentage = flt(doc.get("adjustment_percentage"), PRECISION)
    
    # Validate total_grands is not zero
    if total_grands == 0:
        frappe.throw(_("Total Grands cannot be zero for adjustment percentage calculation"))
    
    # Calculate maximum adjustment limit
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
    return flt(max_limit, PRECISION)


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

