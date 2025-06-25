
import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from optima_zatca.zatca.utils import log_and_throw_error

class CustomSalesInvoice(SalesInvoice):
    def get_gl_entries(self, warehouse_account=None):
        # Get the original GL entries
        gl_entries = super().get_gl_entries(warehouse_account)
        
        # Add your custom GL entries
        self.make_custom_prepayment_gl_entries(gl_entries)
        
        return gl_entries
    
    def make_custom_prepayment_gl_entries(self, gl_entries):
        """Add your custom GL entries here - handles both normal and return invoices"""
        try:
            if self.sales_invoice_type in ["Adjustment", "Final Adjustment"]:
                prepayment_income_account = frappe.db.get_value(
                    "Item Default", 
                    {"parent": "advance payment", "company": self.company}, 
                    "income_account"
                )
                
                tax_account = frappe.db.get_value(
                    "Sales Taxes and Charges",
                    {"parent": self.name, "parenttype": "Sales Invoice"},
                    "account_head"
                )
                
                if not prepayment_income_account:
                    return
                
                # Create GL entries based on return status
                entries = self.get_prepayment_gl_entries(prepayment_income_account, tax_account)
                gl_entries.extend(entries)
                    
        except Exception as e:
            log_and_throw_error(operation="Make Custom GL Entries", document_name=self.name, exception=e)

    def get_prepayment_gl_entries(self, prepayment_income_account, tax_account):
        """Generate GL entries with proper debit/credit logic for returns"""
        try:
            entries = []
            
            # Get account currencies
            prepayment_currency = frappe.get_cached_value("Account", prepayment_income_account, "account_currency")
            tax_currency = frappe.get_cached_value("Account", tax_account, "account_currency") if tax_account else None
            party_currency = frappe.get_cached_value("Account", self.debit_to, "account_currency")
            
            # For returns, flip the debit/credit logic
            if self.is_return:
                # Return invoice: Reverse the original entries
                
                # Credit prepayment income (restore income)
                entries.append(
                    self.get_gl_dict({
                        "account": prepayment_income_account,
                        "against": self.customer,
                        "credit": abs(self.deducted_taxable_amount),
                        "credit_in_account_currency": abs(self.deducted_taxable_amount),
                        "credit_in_transaction_currency": abs(self.deducted_taxable_amount),
                        "cost_center": self.cost_center,
                        "remarks": "Return: Prepayment adjustment reversal",
                    }, prepayment_currency, item=self)
                )
                
                # Credit tax account (restore tax)
                if tax_account and self.deducted_tax_amount:
                    entries.append(
                        self.get_gl_dict({
                            "account": tax_account,
                            "against": self.customer,
                            "credit": abs(self.deducted_tax_amount),
                            "credit_in_account_currency": abs(self.deducted_tax_amount),
                            "credit_in_transaction_currency": abs(self.deducted_tax_amount),
                            "cost_center": self.cost_center,
                            "remarks": "Return: Tax adjustment reversal",
                        }, tax_currency, item=self)
                    )
                
                # Debit customer account (increase receivable)
                entries.append(
                    self.get_gl_dict({
                        "account": self.debit_to,
                        "party_type": "Customer",
                        "party": self.customer,
                        "against": prepayment_income_account,
                        "debit": abs(self.deducted_grand_total),
                        "debit_in_account_currency": abs(self.deducted_grand_total),
                        "debit_in_transaction_currency": abs(self.deducted_grand_total),
                        "cost_center": self.cost_center,
                        "remarks": "Return: Customer adjustment reversal",
                    }, party_currency, item=self)
                )
                
            else:
                # Normal invoice: Original logic
                
                # Debit prepayment income (reduce income)
                entries.append(
                    self.get_gl_dict({
                        "account": prepayment_income_account,
                        "against": self.customer,
                        "debit": abs(self.deducted_taxable_amount),
                        "debit_in_account_currency": abs(self.deducted_taxable_amount),
                        "debit_in_transaction_currency": abs(self.deducted_taxable_amount),
                        "cost_center": self.cost_center,
                        "remarks": "Prepayment adjustment",
                    }, prepayment_currency, item=self)
                )
                
                # Debit tax account
                if tax_account and self.deducted_tax_amount:
                    entries.append(
                        self.get_gl_dict({
                            "account": tax_account,
                            "against": self.customer,
                            "debit": abs(self.deducted_tax_amount),
                            "debit_in_account_currency": abs(self.deducted_tax_amount),
                            "debit_in_transaction_currency": abs(self.deducted_tax_amount),
                            "cost_center": self.cost_center,
                            "remarks": "Tax adjustment",
                        }, tax_currency, item=self)
                    )
                
                # Credit customer account (reduce receivable)
                entries.append(
                    self.get_gl_dict({
                        "account": self.debit_to,
                        "party_type": "Customer",
                        "party": self.customer,
                        "against": prepayment_income_account,
                        "credit": abs(self.deducted_grand_total),
                        "credit_in_account_currency": abs(self.deducted_grand_total),
                        "credit_in_transaction_currency": abs(self.deducted_grand_total),
                        "cost_center": self.cost_center,
                        "remarks": "Customer adjustment",
                    }, party_currency, item=self)
                )
            
            return entries
        except Exception as e:
            log_and_throw_error(operation="Get Prepayment GL Entries", document_name=self.name, exception=e)