frappe.pages['vat_ledger'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'VAT Ledger',
        single_column: true
    });

    // Add HTML structure
    $(page.body).html(`
        <div class="vat-ledger-page" style="padding: 20px;">
            <!-- Filters Section -->
            <div class="row" style="margin-bottom: 20px;">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header" style="background-color: #000000; color: white;">
                            <h5 style="margin: 0;">
                                <i class="fa fa-filter"></i> Report Filters
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-3">
                                    <div class="form-group">
                                        <label for="company_filter">Company</label>
                                        <select class="form-control" id="company_filter">
                                            <option value="">Select Company</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="form-group">
                                        <label for="from_date">From Date</label>
                                        <input type="date" class="form-control" id="from_date">
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="form-group">
                                        <label for="to_date">To Date</label>
                                        <input type="date" class="form-control" id="to_date">
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="form-group">
                                        <label for="tax_account_filter">Tax Account</label>
                                        <select class="form-control" id="tax_account_filter">
                                            <option value="">All Tax Accounts</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="form-group">
                                        <label>&nbsp;</label>
                                        <button id="apply_filters_btn" class="btn btn-primary btn-block">
                                            <i class="fa fa-search"></i> Apply Filters
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Header with Refresh Button -->
            <div class="row" style="margin-bottom: 20px;">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-body" style="text-align: center;">
                            <h3 style="margin-bottom: 15px; color: #2c3e50;">
                                <i class="fa fa-bar-chart"></i> VAT Ledger - Tax Analysis
                            </h3>
                            <p style="font-size: 16px; color: #7f8c8d; margin-bottom: 15px;">
                                <strong>Period:</strong> <span id="date_range_display"></span> |
                                <strong>Time:</strong> <span id="current_time"></span>
                            </p>
                            <button id="refresh_btn" class="btn btn-primary btn-lg px-5 py-3"
                                style="border-radius: 8px; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <i class="fa fa-refresh"></i> Refresh Data
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Data Section -->
            <div id="data_section" style="display: none;">
                <!-- Chart Section -->
                <div class="row" style="margin-bottom: 20px;">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-body" style="padding: 40px; text-align: center;">
                                <div id="vat_chart">
                                    <!-- Chart will be rendered here -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Summary Cards -->
                <div class="row" style="margin-bottom: 20px;">
                    <div class="col-md-12">
                        <div id="summary_cards" class="row">
                            <!-- Summary cards will be rendered here -->
                        </div>
                    </div>
                </div>

                <!-- Data Table Section -->
                <div class="row">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header" style="background-color: #000000; color: white; cursor: pointer;"
                                onclick="$('#vat_table_container').slideToggle(); $('#table_toggle_icon').toggleClass('fa-chevron-down fa-chevron-up');">
                                <h5 class="card-title" style="margin: 0; display: flex; justify-content: space-between; align-items: center;">
                                    <span style="color: white;">
                                        <i class="fa fa-list"></i> VAT Transactions
                                    </span>
                                    <i id="table_toggle_icon" class="fa fa-chevron-up" style="color: white;"></i>
                                </h5>
                            </div>
                            <div class="card-body" id="vat_table_container" style="display: none;">
                                <div class="table-responsive">
                                    <table id="vat_data_table" class="table table-bordered table-hover">
                                        <thead style="background-color: #f8f9fa;">
                                            <tr>
                                                <th>Name</th>
                                                <th>Posting Date</th>
                                                <th>Voucher Type</th>
                                                <th>Tax Account</th>
                                                <th>Tax ID</th>
                                                <th>Party Type</th>
                                                <th>Party</th>
                                                <th>Tax Amount</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <!-- Data will be populated here -->
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);

    // Initialize the page
    let vat_ledger = new VATLedger(page);
};

class VATLedger {
    constructor(page) {
        this.page = page;
        this.init();
    }

    init() {
        this.setup_filters();
        this.bind_events();
        this.update_time();
        setInterval(() => this.update_time(), 1000);
    }

    setup_filters() {
        // Load companies
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Company',
                fields: ['name'],
                limit_page_length: 0
            },
            callback: (r) => {
                if (r.message) {
                    let company_filter = $('#company_filter');
                    r.message.forEach(company => {
                        company_filter.append(`<option value="${company.name}">${company.name}</option>`);
                    });
                    
                    // Set default company
                    if (frappe.defaults.get_default('company')) {
                        company_filter.val(frappe.defaults.get_default('company'));
                        this.load_tax_accounts(frappe.defaults.get_default('company'));
                    }
                }
            }
        });

        // Set default dates (current month)
        let today = new Date();
        let first_day = new Date(today.getFullYear(), today.getMonth(), 1);
        $('#from_date').val(frappe.datetime.obj_to_str(first_day));
        $('#to_date').val(frappe.datetime.obj_to_str(today));

        // Company change event
        $('#company_filter').change(() => {
            let company = $('#company_filter').val();
            if (company) {
                this.load_tax_accounts(company);
            }
        });
    }

    load_tax_accounts(company) {
        frappe.call({
            method: 'optima_zatca.optima_zatca.page.vat_ledger.vat_ledger.get_tax_accounts',
            args: {
                company: company
            },
            callback: (r) => {
                let tax_account_filter = $('#tax_account_filter');
                tax_account_filter.html('<option value="">All Tax Accounts</option>');
                
                if (r.message) {
                    r.message.forEach(account => {
                        tax_account_filter.append(`<option value="${account}">${account}</option>`);
                    });
                }
            }
        });
    }

    bind_events() {
        $('#apply_filters_btn').click(() => this.refresh_data());
        $('#refresh_btn').click(() => this.refresh_data());
    }

    refresh_data() {
        let company = $('#company_filter').val();
        let from_date = $('#from_date').val();
        let to_date = $('#to_date').val();
        let tax_account = $('#tax_account_filter').val();

        if (!company) {
            frappe.msgprint(__('Please select a company'));
            return;
        }

        if (!from_date || !to_date) {
            frappe.msgprint(__('Please select date range'));
            return;
        }

        // Update date range display
        $('#date_range_display').text(`${from_date} to ${to_date}`);

        // Show loading
        frappe.show_progress(__('Loading'), 50, 100, __('Fetching VAT data...'));

        frappe.call({
            method: 'optima_zatca.optima_zatca.page.vat_ledger.vat_ledger.get_vat_ledger_data',
            args: {
                company: company,
                from_date: from_date,
                to_date: to_date,
                tax_account: tax_account
            },
            callback: (r) => {
                frappe.hide_progress();
                
                if (r.message) {
                    this.render_data(r.message);
                    $('#data_section').show();
                    
                    // Scroll to data section
                    $('html, body').animate({
                        scrollTop: $('#data_section').offset().top - 100
                    }, 500);
                }
            },
            error: () => {
                frappe.hide_progress();
            }
        });
    }

    render_data(data) {
        // Render summary cards
        this.render_summary_cards(data.summary);
        
        // Render chart
        this.render_chart(data.chart_data);
        
        // Render table
        this.render_table(data.data);
    }

    render_summary_cards(summary) {
        const gradients = [
            'linear-gradient(82.59deg, #00c48c 0%, #00a173 100%)',
            'linear-gradient(81.67deg, #0084f4 0%, #1a4da2 100%)',
            'linear-gradient(69.83deg, #0084f4 0%, #00c48c 100%)',
            'linear-gradient(81.67deg, #ff647c 0%, #1f5dc5 100%)'
        ];

        let html = '';
        summary.forEach((item, index) => {
            let gradient = gradients[index % gradients.length];
            html += `
                <div class="col-md-3 mb-3">
                    <div class="card" style="background: ${gradient}; color: white; border: none; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div class="card-body text-center">
                            <h6 style="color: white; opacity: 0.9; margin-bottom: 10px;">${item.label}</h6>
                            <h3 style="color: white; font-weight: bold; margin: 0;">${format_currency(item.value)}</h3>
                        </div>
                    </div>
                </div>
            `;
        });
        
        $('#summary_cards').html(html);
    }

    render_chart(chart_data) {
        if (!chart_data || !chart_data.labels || chart_data.labels.length === 0) {
            $('#vat_chart').html('<p style="color: #7f8c8d;">No data available for chart</p>');
            return;
        }

        // Clear previous chart
        $('#vat_chart').html('');

        new frappe.Chart('#vat_chart', {
            title: 'VAT Distribution by Type',
            data: {
                labels: chart_data.labels,
                datasets: [{
                    values: chart_data.values
                }]
            },
            type: 'donut',
            height: 300,
            colors: ['#3AA6B9', '#FFD0D0', '#FF9EAA', '#00c48c', '#0084f4']
        });
    }

    render_table(data) {
        let tbody = $('#vat_data_table tbody');
        tbody.empty();

        if (!data || data.length === 0) {
            tbody.append('<tr><td colspan="8" class="text-center">No data found</td></tr>');
            return;
        }

        data.forEach(row => {
            // Check if it's a header row
            if (row.name && row.name.includes('<h5')) {
                tbody.append(`
                    <tr style="background-color: #f8f9fa;">
                        <td colspan="8">${row.name}</td>
                    </tr>
                `);
            }
            // Check if it's a total row
            else if (row.name && row.name.includes('Total')) {
                tbody.append(`
                    <tr style="background-color: #fff3cd; font-weight: bold;">
                        <td colspan="7">${row.name}</td>
                        <td class="text-right">${format_currency(row.base_tax_amount || 0)}</td>
                    </tr>
                `);
            }
            // Check if it's an empty row
            else if (!row.name && !row.base_tax_amount) {
                tbody.append('<tr><td colspan="8">&nbsp;</td></tr>');
            }
            // Regular data row
            else {
                let name_link = row.name;
                if (row.parenttype && row.name) {
                    name_link = `<a href="/app/${row.parenttype.toLowerCase().replace(/ /g, '-')}/${row.name}" target="_blank">${row.name}</a>`;
                }
                
                tbody.append(`
                    <tr>
                        <td>${name_link}</td>
                        <td>${row.posting_date || ''}</td>
                        <td>${row.parenttype || ''}</td>
                        <td>${row.tax_account || ''}</td>
                        <td>${row.tax_id || ''}</td>
                        <td>${row.party_type || ''}</td>
                        <td>${row.party || ''}</td>
                        <td class="text-right">${format_currency(row.base_tax_amount || 0)}</td>
                    </tr>
                `);
            }
        });
    }

    update_time() {
        let now = new Date();
        $('#current_time').text(now.toLocaleTimeString());
    }
}
