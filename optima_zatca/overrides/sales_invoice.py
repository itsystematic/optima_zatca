import frappe
from frappe.utils import flt, cint

from optima_zatca.zatca.utils import log_and_throw_error
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class CustomSalesInvoice(SalesInvoice):
    ADVANCE_PAYMENT_ITEM = "advance payment"
    ADJUSTMENT_TYPES = ["Adjustment", "Final Adjustment"]
    
    def get_gl_entries(self, warehouse_account=None):
        """Override to add custom prepayment GL entries"""
        gl_entries = super().get_gl_entries(warehouse_account)
        self.make_custom_prepayment_gl_entries(gl_entries)
        return gl_entries
    
    def make_custom_prepayment_gl_entries(self, gl_entries):
        """Add custom GL entries for prepayment adjustments"""
        try:
            if not self._should_create_prepayment_entries():
                return
            
            accounts = self._get_required_accounts()
            if not accounts.get('prepayment_income_account'):
                frappe.log_error(
                    f"No prepayment income account found for Item {self.ADVANCE_PAYMENT_ITEM} in company {self.company}",
                    "Custom GL Entries"
                )
                return
            
            entries = self._create_prepayment_gl_entries(accounts)
            gl_entries.extend(entries)
                    
        except Exception as e:
            log_and_throw_error(
                operation="Make Custom GL Entries", 
                document_name=self.name, 
                exception=e
            )

    def _should_create_prepayment_entries(self):
        """Check if prepayment GL entries should be created"""
        return (
            self.sales_invoice_type in self.ADJUSTMENT_TYPES and
            self._has_required_fields()
        )
    
    def _has_required_fields(self):
        """Validate required custom fields exist"""
        required_fields = ['deducted_taxable_amount', 'deducted_grand_total']
        return all(hasattr(self, field) and getattr(self, field) for field in required_fields)
    
    def _get_required_accounts(self):
        """Fetch all required accounts in a single query where possible"""
        try:
            # Get prepayment income account from Initial Prepayment invoice
            prepayment_income_account = None
            
            # Find the Initial Prepayment row in prepayments_invcoies child table
            initial_prepayment_row = None
            for row in self.get("prepayments_invcoies", []):
                if row.prepayment_type == "Initial Prepayment":
                    initial_prepayment_row = row
                    break
            
            if initial_prepayment_row and initial_prepayment_row.reference_invoice:
                # Get the income account from the first item in the Initial Prepayment invoice
                prepayment_income_account = frappe.db.get_value(
                    "Sales Invoice Item",
                    {
                        "parent": initial_prepayment_row.reference_invoice,
                        "parenttype": "Sales Invoice",
                        "idx": 1  # First row because intial prepayment has only one item
                    },
                    "income_account"
                )
            
            # Get tax account
            tax_account = frappe.db.get_value(
                "Sales Taxes and Charges",
                {
                    "parent": self.name, 
                    "parenttype": "Sales Invoice"
                },
                "account_head"
            )
            
            return {
                'prepayment_income_account': prepayment_income_account,
                'tax_account': tax_account
            }
        except Exception as e:
            frappe.log_error(f"Error fetching accounts: {str(e)}", "Custom GL Entries")
            return {}
        
    def _create_prepayment_gl_entries(self, accounts):
        """Generate GL entries with proper debit/credit logic"""
        try:
            entries = []
            
            # Get account currencies (batch query if possible)
            currencies = self._get_account_currencies(accounts)
            
            if self.is_return:
                entries.extend(self._create_return_entries(accounts, currencies))
            else:
                entries.extend(self._create_normal_entries(accounts, currencies))
            
            return entries
            
        except Exception as e:
            log_and_throw_error(
                operation="Create Prepayment GL Entries", 
                document_name=self.name, 
                exception=e
            )
            return []
        
    def _get_account_currencies(self, accounts):
        """Get currencies for all accounts"""
        currencies = {}
        
        account_list = [
            accounts.get('prepayment_income_account'),
            accounts.get('tax_account'),
            self.debit_to
        ]
        
        for account in filter(None, account_list):
            currencies[account] = frappe.get_cached_value(
                "Account", account, "account_currency"
            )
        
        return currencies
    
    def _create_return_entries(self, accounts, currencies):
        """Create GL entries for return invoices"""
        entries = []
        
        # Use base_ fields if available, fallback to regular fields
        base_taxable = getattr(self, 'base_deducted_taxable_amount', None) or self.deducted_taxable_amount
        base_tax = getattr(self, 'base_deducted_tax_amount', None) or getattr(self, 'deducted_tax_amount', 0)
        base_grand = getattr(self, 'base_deducted_grand_total', None) or self.deducted_grand_total
        
        # Credit prepayment income (restore income)
        entries.append(self._create_gl_entry(
            account=accounts['prepayment_income_account'],
            credit=abs(base_taxable),
            credit_in_account_currency=abs(self.deducted_taxable_amount),
            currency=currencies.get(accounts['prepayment_income_account']),
            remarks="Return: Prepayment adjustment reversal"
        ))
        
        # Credit tax account if exists
        if accounts['tax_account'] and base_tax:
            entries.append(self._create_gl_entry(
                account=accounts['tax_account'],
                credit=abs(base_tax),
                credit_in_account_currency=abs(getattr(self, 'deducted_tax_amount', 0)),
                currency=currencies.get(accounts['tax_account']),
                remarks="Return: Tax adjustment reversal"
            ))
        
        # Debit customer account
        # For receivable account, we need to use transaction currency amount
        deducted_grand_in_party_currency = self.deducted_grand_total
        if self.currency != self.company_currency:
            # Convert base amount to transaction currency
            deducted_grand_in_party_currency = abs(base_grand) / (self.conversion_rate or 1)
        
        entries.append(self._create_gl_entry(
            account=self.debit_to,
            debit=abs(base_grand),
            debit_in_account_currency=abs(deducted_grand_in_party_currency),
            currency=currencies.get(self.debit_to),
            remarks="Return: Customer adjustment reversal",
            party_type="Customer",
            party=self.customer,
            against=accounts['prepayment_income_account']
        ))
        
        return entries
    
    def _create_normal_entries(self, accounts, currencies):
        """Create GL entries for normal invoices"""
        entries = []
        
        # Use base_ fields if available, fallback to regular fields
        base_taxable = getattr(self, 'base_deducted_taxable_amount', None) or self.deducted_taxable_amount
        base_tax = getattr(self, 'base_deducted_tax_amount', None) or getattr(self, 'deducted_tax_amount', 0)
        base_grand = getattr(self, 'base_deducted_grand_total', None) or self.deducted_grand_total
        
        # Debit prepayment income
        entries.append(self._create_gl_entry(
            account=accounts['prepayment_income_account'],
            debit=abs(base_taxable),
            debit_in_account_currency=abs(self.deducted_taxable_amount),
            currency=currencies.get(accounts['prepayment_income_account']),
            remarks="Prepayment adjustment"
        ))
        
        # Debit tax account if exists
        if accounts['tax_account'] and base_tax:
            entries.append(self._create_gl_entry(
                account=accounts['tax_account'],
                debit=abs(base_tax),
                debit_in_account_currency=abs(getattr(self, 'deducted_tax_amount', 0)),
                currency=currencies.get(accounts['tax_account']),
                remarks="Tax adjustment"
            ))
        
        # Credit customer account
        # For receivable account, we need to use transaction currency amount
        deducted_grand_in_party_currency = self.deducted_grand_total
        if self.currency != self.company_currency:
            # Convert base amount to transaction currency
            deducted_grand_in_party_currency = abs(base_grand) / (self.conversion_rate or 1)
        
        entries.append(self._create_gl_entry(
            account=self.debit_to,
            credit=abs(base_grand),
            credit_in_account_currency=abs(deducted_grand_in_party_currency),
            currency=currencies.get(self.debit_to),
            remarks="Customer adjustment",
            party_type="Customer",
            party=self.customer,
            against=accounts['prepayment_income_account']
        ))
        
        return entries
    
    def _create_gl_entry(self, account, currency, remarks, debit=0, credit=0,
                        debit_in_account_currency=None, credit_in_account_currency=None,
                        party_type=None, party=None, against=None):
        """Helper method to create a single GL entry"""
        gl_dict = {
            "account": account,
            "against": against or self.customer,
            "cost_center": self.cost_center,
            "remarks": remarks,
        }
        
        if debit:
            gl_dict.update({
                "debit": debit,
                "debit_in_account_currency": debit_in_account_currency if debit_in_account_currency is not None else debit,
            })
        
        if credit:
            gl_dict.update({
                "credit": credit,
                "credit_in_account_currency": credit_in_account_currency if credit_in_account_currency is not None else credit,
            })
        
        if party_type and party:
            gl_dict.update({
                "party_type": party_type,
                "party": party,
            })
        
        return self.get_gl_dict(gl_dict, currency, item=self)

    @frappe.whitelist()
    def set_advances(self):
        """
        Override of AccountsController.set_advances
        To make sure deducted grand total is considered while allocating advances
        Reviewe how 'amount' is calculated below
        Returns list of advances against Account, Party, Reference
        """

        res = self.get_advance_entries(
            include_unallocated = not cint(self.get("only_include_allocated_payments"))
        )

        self.set("advances", [])
        advance_allocated = 0
        for d in res:
            if self.get("party_account_currency") == self.company_currency:
                amount = (self.get("base_rounded_total") or self.base_grand_total) - self.get("deducted_grand_total", 0)
            else:
                amount = (self.get("rounded_total") or self.grand_total) - self.get("deducted_grand_total", 0)
            allocated_amount = min(amount - advance_allocated, d.amount)
            advance_allocated += flt(allocated_amount)

            advance_row = {
                "doctype": self.doctype + " Advance",
                "reference_type": d.reference_type,
                "reference_name": d.reference_name,
                "reference_row": d.reference_row,
                "remarks": d.remarks,
                "advance_amount": flt(d.amount),
                "allocated_amount": allocated_amount,
                "ref_exchange_rate": flt(d.exchange_rate),  # exchange_rate of advance entry
                "difference_posting_date": self.posting_date,
            }
            if d.get("paid_from"):
                advance_row["account"] = d.paid_from
            if d.get("paid_to"):
                advance_row["account"] = d.paid_to

            self.append("advances", advance_row)
