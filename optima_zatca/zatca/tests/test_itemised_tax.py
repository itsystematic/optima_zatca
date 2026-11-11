"""How the itemised-tax override reads Frappe 16's tax breakup and turns it into line VAT.

The breakup rows are shaped as `calculate_taxes_and_totals` leaves them in
`doc._item_wise_tax_details`: one per item line and tax, holding the line, the tax row, the
line's rate and its tax amount. Nothing is saved.
"""

import frappe
from frappe.tests import UnitTestCase

from optima_zatca.zatca.itemised_tax import _build_itemised_tax, update_itemised_tax_data


def tax(description, *, category=None, included_in_print_rate=0):
    return frappe._dict(
        description=description,
        account_head=f"{description} - OZT",
        category=category,
        included_in_print_rate=included_in_print_rate,
    )


def breakup(item_code, tax_row, rate, amount):
    return frappe._dict(item=frappe._dict(item_code=item_code), tax=tax_row, rate=rate, amount=amount)


def invoice_at_15_percent(*, amount, included_in_print_rate=0):
    """An unsaved one-line Sales Invoice with its breakup filled in as ERPNext would."""
    doc = frappe.new_doc("Sales Invoice")
    doc.net_total = 100
    line = doc.append("items", {"item_code": "A", "qty": 1, "rate": amount, "amount": amount, "net_amount": 100})
    vat = doc.append(
        "taxes",
        {"charge_type": "On Net Total", "description": "VAT 15%", "rate": 15, "included_in_print_rate": included_in_print_rate},
    )
    doc._item_wise_tax_details = [frappe._dict(item=line, tax=vat, rate=15, amount=15)]
    return doc


class TestBuildItemisedTax(UnitTestCase):
    def test_valuation_charges_are_not_vat(self):
        """A Purchase Invoice's valuation-only charge would otherwise raise the line's VAT rate."""
        itemised = _build_itemised_tax(
            [breakup("A", tax("VAT 15%"), 15, 15), breakup("A", tax("Freight", category="Valuation"), 10, 10)]
        )
        self.assertEqual(list(itemised["A"]), ["VAT 15%"])

    def test_each_tax_on_an_item_keeps_its_own_entry(self):
        """The call sites add up the rates of an item's taxes, so merged entries would drop one."""
        itemised = _build_itemised_tax([breakup("A", tax("VAT 15%"), 15, 15), breakup("A", tax("Excise"), 5, 5)])
        self.assertEqual({name: entry.tax_rate for name, entry in itemised["A"].items()}, {"VAT 15%": 15, "Excise": 5})

    def test_lines_of_one_item_add_amounts_not_rates(self):
        """Frappe 16 breaks tax down per line, not per item code. Two lines of one item under one
        tax are still taxed at 15%, not 30%."""
        vat = tax("VAT 15%")
        entry = _build_itemised_tax([breakup("A", vat, 15, 15), breakup("A", vat, 15, 30)])["A"]["VAT 15%"]
        self.assertEqual((entry.tax_rate, entry.tax_amount), (15, 45))


class TestLineVat(UnitTestCase):
    """The fields ZATCA's invoice lines are built from."""

    fields = ("tax_rate", "tax_amount", "line_extension_amount", "price_amount", "total_amount")

    def test_vat_is_added_to_an_exclusive_price(self):
        doc = invoice_at_15_percent(amount=100)
        update_itemised_tax_data(doc)
        self.assertEqual([doc.items[0].get(field) for field in self.fields], [15, 15, 100, 100, 115])

    def test_vat_is_split_out_of_an_inclusive_price(self):
        """Read as exclusive, a 115 price would report 115 net and 17.25 VAT."""
        doc = invoice_at_15_percent(amount=115, included_in_print_rate=1)
        update_itemised_tax_data(doc)
        self.assertEqual([doc.items[0].get(field) for field in self.fields], [15, 15, 100, 100, 115])
