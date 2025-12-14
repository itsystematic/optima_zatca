// Copyright (c) 2024, IT Systematic and contributors
// For license information, please see license.txt

const ReportSummaryWrapper = document.querySelector('.report-summary')
const gradients = [
	'linear-gradient(82.59deg, #00c48c 0%, #00a173 100%)',
	'linear-gradient(81.67deg, #0084f4 0%, #1a4da2 100%)',
	'linear-gradient(69.83deg, #0084f4 0%, #00c48c 100%)',
	'linear-gradient(81.67deg, #ff647c 0%, #1f5dc5 100%)',
	'linear-gradient(45deg, #ff9a9e 0%, #fecfef 100%)',
	'linear-gradient(60deg, #a18cd1 0%, #fbc2eb 100%)',
	'linear-gradient(90deg, #fad0c4 0%, #ffd1ff 100%)',
	'linear-gradient(120deg, #ffecd2 0%, #fcb69f 100%)',
	'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)',
	'linear-gradient(150deg, #a1c4fd 0%, #c2e9fb 100%)',
	'linear-gradient(165deg, #d4fc79 0%, #96e6a1 100%)',
	'linear-gradient(180deg, #84fab0 0%, #8fd3f4 100%)',
	'linear-gradient(200deg, #a6c0fe 0%, #f68084 100%)',
	'linear-gradient(220deg, #fccb90 0%, #d57eeb 100%)',
	'linear-gradient(240deg, #e0c3fc 0%, #8ec5fc 100%)',
	'linear-gradient(260deg, #f093fb 0%, #f5576c 100%)',
	'linear-gradient(280deg, #4facfe 0%, #00f2fe 100%)',
	'linear-gradient(300deg, #43e97b 0%, #38f9d7 100%)',
	'linear-gradient(320deg, #fa709a 0%, #fee140 100%)',
	'linear-gradient(340deg, #30cfd0 0%, #330867 100%)',
	'linear-gradient(360deg, #ff9a9e 0%, #fecfef 100%)',
	'linear-gradient(45deg, #30cfd0 0%, #330867 100%)',
	'linear-gradient(60deg, #a1c4fd 0%, #c2e9fb 100%)',
	'linear-gradient(75deg, #d4fc79 0%, #96e6a1 100%)'
];
const observer = new MutationObserver((mutationList) => {
	for (const mutation of mutationList) {
		if (mutation.type === 'childList') {
			// To remove borders from the page form that contains filter
			const PageForm = document.querySelector('.page-form')
			PageForm.classList.add('border-0')
			// Select the container containing the items
			// Add custom classes to container
			ReportSummaryWrapper.classList.add('c-dashboardInfo', 'border-0');
			// Select all items
			const ReportSummarySection = document.querySelectorAll(".summary-item");


			const usedGradients = new Set();

			// Loop for every item to add custom classes with random gradiants
			for (let summary_item of ReportSummarySection) {
				summary_item.classList.add('wrap', 'col-md-6');

				let randomGradient;

				do {
					randomGradient = gradients[Math.floor(Math.random() * gradients.length)];
				} while (usedGradients.has(randomGradient));

				summary_item.style.setProperty('--random-gradient', randomGradient);
				usedGradients.add(randomGradient);
			}
		}
	}
})

observer.observe(ReportSummaryWrapper, { childList: true })

frappe.query_reports["Zatca VAT Details"] = {



	onload() {
		frappe.breadcrumbs.add('Accounts');
	},
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1,
		},
		// {
		// 	"fieldname": "type",
		// 	"label": __("Type"),
		// 	"fieldtype": "Link",
		// 	"options": "Tax Category",
		// },
		{
			"fieldname": "tax_account",
			"label": __("Tax Account"),
			"fieldtype": "Link",
			"options": "Account",
			get_query: function () {
				return {
					filters: {
						company: frappe.query_report.get_filter_value('company'),
						account_type: "Tax",
						is_group: 0,
					}
				}
			}
		},

	],

	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.name == "<h5 style='font-weight:bold; text-align:center; color:#C80036'>Total</h5>" && ['base_tax_amount'].includes(column.fieldname)) {
			value = value.bold();
		}

		return value;
	},

};
