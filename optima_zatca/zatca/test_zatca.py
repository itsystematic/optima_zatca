from frappe.tests.utils import FrappeTestCase
from optima_zatca.zatca.setup import get_registered_companies

class TestZatca(FrappeTestCase):

    def test_company_registered(self):
        
        list_of_companies = get_registered_companies()
        self.assertEqual(len(list_of_companies), 1, "Should be 1")