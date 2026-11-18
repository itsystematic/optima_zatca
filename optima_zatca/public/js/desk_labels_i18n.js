// Translate desk labels that Frappe renders without __(), so locale/ar.po cannot reach them otherwise:
// - module dock: item labels and tooltips (the row title), and the module logo's title
// - sidebar items and section headings
// - attributes built in English: the filter counter ("2 Filters Applied"), the report's
//   "Tree Level" input and the "Search" button title
// Nothing changes when a label has no translation.
(function () {
	const tr = (s) => (typeof s === "string" && s && typeof __ === "function" ? __(s) : s);

	function patch() {
		const ui = window.frappe && frappe.ui;
		if (!ui || !ui.Sidebar || !ui.Dock) return false;

		const S = ui.Sidebar.prototype;
		if (!S.__optima_i18n) {
			const dock_entry = S.dock_entry;
			if (dock_entry) {
				S.dock_entry = function (row) {
					const entry = dock_entry.call(this, row);
					if (entry && entry.label) entry.label = tr(entry.label);
					return entry;
				};
			}
			const make_item = S.make_sidebar_item;
			if (make_item) {
				S.make_sidebar_item = function (opts) {
					const item = opts && opts.item;
					if (item && item.label && !item.__optima_tr) {
						item.label = tr(item.label);
						item.__optima_tr = 1;
					}
					return make_item.call(this, opts);
				};
			}
			S.__optima_i18n = 1;
		}

		const D = ui.Dock.prototype;
		if (!D.__optima_i18n) {
			const name_tile = D.name_tile;
			if (name_tile) {
				D.name_tile = function ($el, label) {
					return name_tile.call(this, $el, tr(label));
				};
			}
			const module_logo = D.module_logo;
			if (module_logo) {
				D.module_logo = function () {
					const logo = module_logo.call(this);
					if (logo && logo.title) logo.title = tr(logo.title);
					return logo;
				};
			}
			D.__optima_i18n = 1;
		}
		return true;
	}

	function translate_attribute(value) {
		const m = value.match(/^(\d+) Filters? Applied$/);
		if (m) return __(+m[1] > 1 ? "{0} Filters Applied" : "{0} Filter Applied", [m[1]]);
		if (value === "Tree Level") return tr("Level");
		if (value === "Search") return tr("Search");
		return null;
	}

	function fix_attributes(root) {
		if (!root || !root.querySelectorAll) return;
		root.querySelectorAll("[title],[aria-label]").forEach((el) => {
			["title", "aria-label"].forEach((name) => {
				const value = el.getAttribute(name);
				if (!value) return;
				const out = translate_attribute(value);
				if (out && out !== value) el.setAttribute(name, out);
			});
		});
	}

	const lang = (window.frappe && frappe.boot && frappe.boot.lang) || document.documentElement.lang;
	if (lang && lang !== "en") {
		let pending = false;
		new MutationObserver(() => {
			if (pending) return;
			pending = true;
			setTimeout(() => {
				pending = false;
				fix_attributes(document.body);
			}, 300);
		}).observe(document.documentElement, { childList: true, subtree: true });
	}

	if (!patch()) {
		let tries = 0;
		const timer = setInterval(() => {
			if (patch() || ++tries > 100) clearInterval(timer);
		}, 50);
	}
})();
