# Copyright (c) 2026, IT Systematic and contributors
# For license information, please see license.txt

"""The results the Advance Payment Report exists to show, on the chains most likely to break it.

Most tests feed build_report rows shaped like get_invoices returns them, so no invoice has to exist.
TestExecute saves one real chain to prove the query reads the right fields and only submitted invoices.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, getdate, nowdate

from optima_zatca.events.tests import helpers
from optima_zatca.optima_zatca.report.advance_payment_report.advance_payment_report import (
    build_report,
    execute,
    parse_filters,
)

CUSTOMER = "Optima Zatca Test Customer"


def invoice(name, invoice_type, posting_date, *, parent=None, is_return=0, taxable=0.0, deducted=0.0, percentage=0.0, **fields):
    """A chain invoice as get_invoices returns it, at 15% VAT."""
    row = frappe._dict(
        name=name,
        posting_date=getdate(posting_date),
        creation=f"{posting_date} 10:00:00",
        customer=CUSTOMER,
        customer_name=CUSTOMER,
        customer_group="Commercial",
        currency="SAR",
        sales_invoice_type=invoice_type,
        is_return=is_return,
        return_against=parent if is_return else None,
        previous_prepayment=parent,
        base_net_total=taxable,
        base_total_taxes_and_charges=taxable * 0.15,
        base_grand_total=taxable * 1.15,
        deducted_taxable_amount=deducted,
        deducted_tax_amount=deducted * 0.15,
        deducted_grand_total=deducted * 1.15,
        adjustment_percentage=percentage,
        clearance_or_reporting="CLEARED",
    )
    row.update(fields)
    return row


def contract():
    """1,000 advanced in two parts, then settled 40% and 60%. The Prepayment carries the Initial's
    600 in its deducted fields, as the client fills them."""
    return [
        invoice("INIT", "Initial Prepayment", "2026-03-02", taxable=600),
        invoice("PRE", "Prepayment", "2026-03-05", parent="INIT", taxable=400, deducted=600),
        invoice("ADJ", "Adjustment", "2026-03-10", parent="PRE", taxable=900, deducted=400, percentage=40),
        invoice("FIN", "Final Adjustment", "2026-03-20", parent="ADJ", taxable=1200, deducted=600, percentage=60),
    ]


def run_report(invoices, **filters):
    filters = parse_filters({"company": "_Test Company", "from_date": "2026-03-01", "to_date": "2026-03-31", **filters})
    _columns, rows, _message, _chart, summary = build_report(invoices, filters, "SAR")
    return rows, {card["label"]: card["value"] for card in summary}


def report(invoices, **filters):
    """The report's rows, less its total row, and its summary cards by label."""
    rows, cards = run_report(invoices, **filters)
    return [row for row in rows if not row.get("is_total_row")], cards


def total_row(invoices, **filters):
    return run_report(invoices, **filters)[0][-1]


def chain_rows(rows):
    return [row for row in rows if row["indent"] == 0]


class TestAdvancePaymentReport(FrappeTestCase):
    def test_a_real_contract_settles_to_zero(self):
        """Three advances settled by three adjustments, with figures as stored in production.

        Its Prepayments carry 129,961.74 and 246,732.18 in deducted_taxable_amount. Counting those
        would close the chain at -376,693.92. Its percentages sum to 99.99999796, which rounded one by
        one would total 100.01%.
        """
        invoices = [
            invoice("INIT", "Initial Prepayment", "2026-07-16", taxable=129961.74),
            invoice("PRE-1", "Prepayment", "2026-07-16", parent="INIT", taxable=116770.44, deducted=129961.74),
            invoice("PRE-2", "Prepayment", "2026-07-16", parent="PRE-1", taxable=117855.5, deducted=246732.18),
            invoice(
                "ADJ-1", "Adjustment", "2026-07-16",
                parent="PRE-2", taxable=146026.55, deducted=116770.441250841, percentage=32.02808,
            ),
            invoice(
                "ADJ-2", "Adjustment", "2026-07-17",
                parent="ADJ-1", taxable=163917.6, deducted=117855.502100634, percentage=32.32569518,
            ),
            invoice(
                "FIN", "Final Adjustment", "2026-07-17",
                parent="ADJ-2", taxable=161763.2, deducted=129961.736641234, percentage=35.64622278,
            ),
        ]
        rows, cards = report(invoices, from_date="2026-07-01", to_date="2026-07-31")
        chain, *lines = rows

        self.assertEqual([line["invoice"] for line in lines], [row.name for row in invoices])
        self.assertEqual(
            [line["prepayment_amount"] for line in lines],
            [129961.74, 116770.44, 117855.5, -116770.44, -117855.5, -129961.74],
        )
        self.assertEqual((chain["balance"], chain["status"]), (0, "Closed"))
        self.assertEqual((chain["adjustment_percentage"], chain["remaining_percentage"]), (100, 0))
        self.assertEqual(cards["Advances Invoiced in Period"], 364587.68)
        self.assertEqual(cards["Advances Deducted in Period"], 364587.68)
        self.assertEqual(cards["Closing Advance Balance"], 0)

    def test_each_balance_moves_by_the_advance_and_deduction_beside_it(self):
        """The Prepayment's own 400 shows as its advance, and the 600 the client copied into its
        deducted fields does not. The balance moves by the taxable amount, not the total."""
        chain, *lines = report(contract())[0]
        fields = ("prepayment_amount", "prepayment_tax", "prepayment_total", "balance")

        self.assertEqual(
            [tuple(line[field] for field in fields) for line in lines],
            [(600, 90, 690, 600), (400, 60, 460, 1000), (-400, -60, -460, 600), (-600, -90, -690, 0)],
        )
        self.assertEqual([chain[field] for field in fields], [0, 0, 0, 0], "a settled chain nets to zero")

    def test_only_the_chain_row_shows_what_remains(self):
        """An invoice row's Remaining % is null, since Frappe prints a missing one as 0%."""
        chain, *lines = report(contract()[:3])[0]

        self.assertEqual(chain["remaining_percentage"], 60)
        self.assertEqual({line["remaining_percentage"] for line in lines}, {None})

    def test_returning_the_final_adjustment_reopens_the_chain(self):
        invoices = contract() + [
            invoice(
                "RET", "Final Adjustment", "2026-03-25",
                is_return=1, parent="FIN", taxable=-1200, deducted=-600, percentage=60,
            )
        ]
        rows, _cards = report(invoices)
        chain, returned = rows[0], rows[-1]

        self.assertEqual((chain["status"], chain["balance"], chain["remaining_percentage"]), ("Open", 600, 60))
        self.assertEqual(returned["invoice_type"], "Final Adjustment (Return)")
        self.assertEqual((returned["prepayment_amount"], returned["adjustment_percentage"]), (600, -60))

    def test_the_period_rolls_the_advance_forward(self):
        invoices = [
            invoice("INIT", "Initial Prepayment", "2026-02-15", taxable=1000),
            invoice("ADJ", "Adjustment", "2026-03-10", parent="INIT", deducted=300, percentage=30),
            invoice("PRE", "Prepayment", "2026-03-12", parent="ADJ", taxable=500),
            invoice("AFTER", "Adjustment", "2026-04-05", parent="PRE", deducted=200, percentage=20),
            invoice("SETTLED", "Initial Prepayment", "2026-02-01", taxable=700),
            invoice("SETTLED-FIN", "Final Adjustment", "2026-02-20", parent="SETTLED", deducted=700, percentage=100),
        ]
        rows, cards = report(invoices)

        self.assertEqual([row["invoice"] for row in chain_rows(rows)], ["INIT"], "a chain settled before the period is out")
        self.assertEqual([(row["invoice"], row["out_of_range"]) for row in rows[1:]], [("INIT", 1), ("ADJ", 0), ("PRE", 0)])
        self.assertEqual(
            [cards[label] for label in ("Opening Advance Balance", "Advances Invoiced in Period", "Advances Deducted in Period", "Closing Advance Balance")],
            [1000, 500, 300, 1200],
        )

    def test_the_status_filter_keeps_the_cards_to_its_chains(self):
        invoices = contract() + [invoice("UNSETTLED", "Initial Prepayment", "2026-03-15", taxable=500)]
        for status, chains, closing in (("Open", ["UNSETTLED"], 500), ("Closed", ["INIT"], 0)):
            with self.subTest(status=status):
                rows, cards = report(invoices, status=status)
                self.assertEqual([row["invoice"] for row in chain_rows(rows)], chains)
                self.assertEqual(cards["Closing Advance Balance"], closing)

    def test_a_backdated_adjustment_still_follows_its_advance(self):
        rows, _cards = report(
            [
                invoice("ADJ", "Adjustment", "2026-03-01", parent="INIT", deducted=100, percentage=20),
                invoice("INIT", "Initial Prepayment", "2026-03-10", taxable=500),
            ]
        )
        self.assertEqual([(row["invoice"], row["balance"]) for row in rows[1:]], [("INIT", 500), ("ADJ", 400)])
        self.assertEqual(rows[0]["chain_period"], 9, "the period runs between dates, not along the links")

    def test_an_adjustment_whose_advance_is_gone_roots_its_own_chain(self):
        rows, _cards = report(
            [
                invoice("INIT", "Initial Prepayment", "2026-03-02", taxable=1000),
                invoice("ORPHAN", "Adjustment", "2026-03-06", parent="CANCELLED", deducted=100, percentage=10),
            ]
        )
        self.assertEqual([(row["invoice"], row["balance"]) for row in chain_rows(rows)], [("INIT", 1000), ("ORPHAN", -100)])

    def test_a_sales_order_finds_the_adjustments_of_its_chain(self):
        invoices = contract()
        invoices[0].prepayment_sales_order = "SO-1"

        rows, _cards = report(invoices, approach="Adjustment", sales_order="SO-1")
        self.assertEqual([(row["invoice"], row["chain"]) for row in rows], [("ADJ", "INIT"), ("FIN", "INIT")])
        self.assertNotIn("indent", rows[0], "an indent would turn the flat list into a tree")
        self.assertEqual(run_report(invoices, approach="Adjustment", sales_order="SO-2")[0], [], "nothing to total")

    def test_a_flat_total_nets_the_amounts_and_averages_the_percentage(self):
        """The return adds back what its Final Adjustment deducted, and its -60% counts in the mean."""
        invoices = contract() + [
            invoice(
                "RET", "Final Adjustment", "2026-03-25",
                is_return=1, parent="FIN", taxable=-1200, deducted=-600, percentage=60,
            )
        ]
        total = total_row(invoices, approach="Adjustment")
        fields = ("prepayment_amount", "prepayment_tax", "prepayment_total", "adjustment_percentage")

        self.assertEqual([total[field] for field in fields], [-400, -60, -460, 13.33])
        self.assertNotIn("indent", total, "an indent would turn the flat list into a tree")

    def test_the_chain_total_counts_each_chain_once(self):
        """Summed with their invoices, the chains' amounts would double. The settled contract has no
        days since its last invoice, so that mean is the open chain's alone."""
        invoices = contract() + [
            invoice("OPEN", "Initial Prepayment", "2026-03-15", taxable=500),
            invoice("OPEN-ADJ", "Adjustment", "2026-03-25", parent="OPEN", deducted=200, percentage=40),
        ]
        total = total_row(invoices)
        fields = (
            "prepayment_amount", "prepayment_tax", "prepayment_total",
            "adjustment_percentage", "remaining_percentage", "chain_period", "days_since_last_invoice",
        )

        self.assertEqual([total[field] for field in fields], [300, 45, 345, 70, 30, 14, 6])
        self.assertIsNone(total["balance"], "a running balance has no total")


class TestExecute(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_the_report_reads_submitted_chains(self):
        """Submitting runs the ZATCA path, so the chain is saved as drafts and marked submitted."""
        today = getdate(nowdate())
        initial = helpers.make_sales_invoice(sales_invoice_type="Initial Prepayment")
        helpers.make_prepayment_invoice(id=initial.name)
        adjustment = helpers.make_sales_invoice(
            sales_invoice_type="Adjustment",
            previous_prepayment=initial.name,
            adjustment_percentage=40,
            total_grands=initial.base_grand_total,
            deducted_taxable_amount=flt(initial.base_net_total * 0.4, 2),
            deducted_tax_amount=flt(initial.base_total_taxes_and_charges * 0.4, 2),
            deducted_grand_total=flt(initial.base_grand_total * 0.4, 2),
        )
        frappe.db.set_value("Sales Invoice", initial.name, {"docstatus": 1, "posting_date": add_days(today, -10)})
        frappe.db.set_value("Sales Invoice", adjustment.name, "docstatus", 1)
        helpers.make_sales_invoice(sales_invoice_type="Adjustment")

        _columns, rows, _message, _chart, _summary = execute(
            {
                "company": helpers.get_company(),
                "from_date": today,
                "to_date": today,
                "customer": helpers.get_or_create_customer(),
            }
        )

        self.assertEqual([row["invoice"] for row in rows], [initial.name, initial.name, adjustment.name, "Total"])
        self.assertEqual(rows[0]["balance"], flt(initial.base_net_total - adjustment.deducted_taxable_amount, 2))
        self.assertEqual(
            [(row["prepayment_tax"], row["prepayment_total"]) for row in rows[1:3]],
            [
                (initial.base_total_taxes_and_charges, initial.base_grand_total),
                (-adjustment.deducted_tax_amount, -adjustment.deducted_grand_total),
            ],
        )
