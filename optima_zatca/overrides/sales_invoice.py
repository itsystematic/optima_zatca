import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from optima_zatca.zatca.utils import log_and_throw_error

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
        
        # Credit prepayment income (restore income)
        entries.append(self._create_gl_entry(
            account=accounts['prepayment_income_account'],
            credit=abs(self.deducted_taxable_amount),
            currency=currencies.get(accounts['prepayment_income_account']),
            remarks="Return: Prepayment adjustment reversal"
        ))
        
        # Credit tax account if exists
        if accounts['tax_account'] and getattr(self, 'deducted_tax_amount', 0):
            entries.append(self._create_gl_entry(
                account=accounts['tax_account'],
                credit=abs(self.deducted_tax_amount),
                currency=currencies.get(accounts['tax_account']),
                remarks="Return: Tax adjustment reversal"
            ))
        
        # Debit customer account
        entries.append(self._create_gl_entry(
            account=self.debit_to,
            debit=abs(self.deducted_grand_total),
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
        
        # Debit prepayment income
        entries.append(self._create_gl_entry(
            account=accounts['prepayment_income_account'],
            debit=abs(self.deducted_taxable_amount),
            currency=currencies.get(accounts['prepayment_income_account']),
            remarks="Prepayment adjustment"
        ))
        
        # Debit tax account if exists
        if accounts['tax_account'] and getattr(self, 'deducted_tax_amount', 0):
            entries.append(self._create_gl_entry(
                account=accounts['tax_account'],
                debit=abs(self.deducted_tax_amount),
                currency=currencies.get(accounts['tax_account']),
                remarks="Tax adjustment"
            ))
        
        # Credit customer account
        entries.append(self._create_gl_entry(
            account=self.debit_to,
            credit=abs(self.deducted_grand_total),
            currency=currencies.get(self.debit_to),
            remarks="Customer adjustment",
            party_type="Customer",
            party=self.customer,
            against=accounts['prepayment_income_account']
        ))
        
        return entries
    
    def _create_gl_entry(self, account, currency, remarks, debit=0, credit=0, 
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
                "debit_in_account_currency": debit,
                "debit_in_transaction_currency": debit,
            })
        
        if credit:
            gl_dict.update({
                "credit": credit,
                "credit_in_account_currency": credit,
                "credit_in_transaction_currency": credit,
            })
        
        if party_type and party:
            gl_dict.update({
                "party_type": party_type,
                "party": party,
            })
        
        return self.get_gl_dict(gl_dict, currency, item=self)