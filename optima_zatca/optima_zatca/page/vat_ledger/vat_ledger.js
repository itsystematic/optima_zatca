frappe.pages['vat_ledger'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'VAT Ledger',
        single_column: true
    });

    // Add custom styles
    $('head').append(`
        <style>
            .vat-ledger-page {
                padding: 20px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
            }
            
            .filter-card {
                background: white;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                border: none;
                overflow: hidden;
                animation: slideInDown 0.5s ease;
            }
            
            .filter-card .card-header {
                background: linear-gradient(135deg, #400434 0%, #7d0b66 100%);
                border: none;
                padding: 15px 25px;
            }
            
            .filter-card .card-header h5 {
                color: white;
                margin: 0;
                font-weight: 600;
                font-size: 18px;
            }
            
            .filter-card .card-body {
                padding: 25px;
            }
            
            .form-group label {
                font-weight: 600;
                color: #495057;
                margin-bottom: 8px;
                font-size: 14px;
            }
            
            .form-control {
                border-radius: 8px;
                border: 2px solid #e9ecef;
                padding: 10px 15px;
                transition: all 0.3s ease;
            }
            
            .form-control:focus {
                border-color: #a60f88;
                box-shadow: 0 0 0 0.2rem rgba(166, 15, 136, 0.25);
            }
            
            .header-card {
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                border: none;
                overflow: hidden;
                animation: fadeInUp 0.6s ease;
            }
            
            .header-card .card-body {
                padding: 40px;
                text-align: center;
                background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            }
            
            .header-title {
                margin-bottom: 20px;
                color: #2c3e50;
                font-weight: 700;
                font-size: 32px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.05);
            }
            
            .header-info {
                font-size: 16px;
                color: #6c757d;
                margin-bottom: 25px;
                padding: 15px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }
            
            .refresh-btn {
                background: linear-gradient(135deg, #590649 0%, #a60f88 100%);
                border: none;
                border-radius: 50px;
                padding: 15px 50px;
                font-weight: 600;
                font-size: 16px;
                box-shadow: 0 5px 20px rgba(166, 15, 136, 0.4);
                transition: all 0.3s ease;
                color: white;
            }
            
            .refresh-btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(166, 15, 136, 0.5);
            }
            
            .refresh-btn:active {
                transform: translateY(0);
            }
            
            .summary-card-enhanced {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.08);
                border: none;
                position: relative;
                overflow: hidden;
                transition: all 0.3s ease;
                animation: fadeInUp 0.7s ease;
            }
            
            .summary-card-enhanced::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 5px;
                background: var(--card-gradient);
            }
            
            .summary-card-enhanced:hover {
                transform: translateY(-8px);
                box-shadow: 0 12px 30px rgba(0,0,0,0.15);
            }
            
            .summary-card-label {
                font-size: 14px;
                color: #6c757d;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 12px;
            }
            
            .summary-card-value {
                font-size: 36px;
                font-weight: 800;
                background: var(--card-gradient);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 10px;
            }
            
            .summary-card-icon {
                position: absolute;
                right: 20px;
                top: 20px;
                font-size: 40px;
                opacity: 0.15;
            }
            
            .chart-container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.08);
                border: none;
                overflow: hidden;
                animation: fadeIn 0.8s ease;
            }
            
            .chart-container .card-body {
                padding: 40px;
            }
            
            .table-card {
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.08);
                border: none;
                overflow: hidden;
                animation: fadeInUp 0.9s ease;
            }
            
            .table-card .card-header {
                background: linear-gradient(135deg, #400434 0%, #7d0b66 100%);
                border: none;
                padding: 20px 30px;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .table-card .card-header:hover {
                background: linear-gradient(135deg, #590649 0%, #a60f88 100%);
            }
            
            .table-card .card-header h5 {
                color: white;
                margin: 0;
                font-weight: 600;
                font-size: 18px;
            }
            
            .table-responsive {
                max-height: 600px;
                overflow-y: auto;
            }
            
            #vat_data_table {
                margin: 0;
            }
            
            #vat_data_table thead {
                position: sticky;
                top: 0;
                z-index: 10;
                background: #f8f9fa;
            }
            
            #vat_data_table thead th {
                background: linear-gradient(135deg, #400434 0%, #a60f88 100%);
                color: white;
                border: none;
                padding: 15px;
                font-weight: 600;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            #vat_data_table tbody tr {
                transition: all 0.2s ease;
            }
            
            #vat_data_table tbody tr:hover:not(.no-hover) {
                background: #f8f9fa;
                transform: scale(1.01);
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }
            
            #vat_data_table tbody tr.no-hover {
                cursor: default;
            }
            
            #vat_data_table tbody td {
                padding: 15px;
                vertical-align: middle;
                border-color: #e9ecef;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 200px;
            }
            
            #vat_data_table tbody td:nth-child(1),
            #vat_data_table thead th:nth-child(1) {
                width: 230px;
                min-width: 230px;
                max-width: 230px;
            }
            
            #vat_data_table tbody td:nth-child(2),
            #vat_data_table thead th:nth-child(2) {
                width: 150px;
                min-width: 150px;
                max-width: 150px;
            }
            
            #vat_data_table tbody td:nth-child(4),
            #vat_data_table thead th:nth-child(4) {
                width: 155px;
                min-width: 155px;
                max-width: 155px;
            }
            
            .group-header-row {
                background: linear-gradient(135deg, #590649 0%, #7d0b66 100%);
                color: white !important;
            }
            
            .group-header-row td {
                font-weight: 700;
                text-align: center;
                padding: 15px !important;
                font-size: 16px;
                border: none !important;
            }
            
            .group-total-row {
                background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
                font-weight: 700;
            }
            
            .group-total-row td {
                padding: 15px !important;
                border-top: 3px solid #a60f88 !important;
            }
            
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(255, 255, 255, 0.95);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            }
            
            .loading-spinner {
                text-align: center;
            }
            
            .spinner-border {
                width: 60px;
                height: 60px;
                border: 6px solid #f3f3f3;
                border-top: 6px solid #a60f88;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes fadeInUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            @keyframes slideInDown {
                from {
                    opacity: 0;
                    transform: translateY(-30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .btn-primary {
                background: linear-gradient(135deg, #590649 0%, #a60f88 100%);
                border: none;
                border-radius: 8px;
                padding: 10px 25px;
                font-weight: 600;
                transition: all 0.3s ease;
            }
            
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(166, 15, 136, 0.4);
            }
            
            .empty-state {
                text-align: center;
                padding: 60px 20px;
                color: #6c757d;
            }
            
            .empty-state i {
                font-size: 64px;
                margin-bottom: 20px;
                opacity: 0.3;
            }
        </style>
    `);

    // Add HTML structure
    $(page.body).html(`
        <div class="vat-ledger-page">
            <!-- Filters Section -->
            <div class="row" style="margin-bottom: 25px;">
                <div class="col-md-12">
                    <div class="card filter-card">
                        <div class="card-header">
                            <h5>
                                <i class="fa fa-filter"></i> Report Filters
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-2">
                                    <div class="form-group">
                                        <label for="company_filter"><i class="fa fa-building"></i> Company</label>
                                        <select class="form-control" id="company_filter">
                                            <option value="">Select Company</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="form-group">
                                        <label for="from_date"><i class="fa fa-calendar"></i> From Date</label>
                                        <input type="date" class="form-control" id="from_date">
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="form-group">
                                        <label for="to_date"><i class="fa fa-calendar"></i> To Date</label>
                                        <input type="date" class="form-control" id="to_date">
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="form-group">
                                        <label for="tax_account_filter"><i class="fa fa-university"></i> Tax Account</label>
                                        <select class="form-control" id="tax_account_filter">
                                            <option value="">All Tax Accounts</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="form-group">
                                        <label for="party_filter"><i class="fa fa-user"></i> Party</label>
                                        <input type="text" class="form-control" id="party_filter" placeholder="Search party...">
                                    </div>
                                </div>
                                <div class="col-md-2">
                                    <div class="form-group">
                                        <label>&nbsp;</label>
                                        <button id="apply_filters_btn" class="btn btn-primary btn-block">
                                            <i class="fa fa-search"></i> Apply
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Header with Refresh Button -->
            <div class="row" style="margin-bottom: 30px;">
                <div class="col-md-12">
                    <div class="card header-card">
                        <div class="card-body">
                            <h3 class="header-title">
                                <i class="fa fa-line-chart"></i> VAT Ledger - Tax Analysis
                            </h3>
                            <div class="header-info">
                                <strong><i class="fa fa-calendar-check-o"></i> Period:</strong> <span id="date_range_display">Select dates and apply filters</span>
                                <span style="margin: 0 15px;">|</span>
                                <strong><i class="fa fa-clock-o"></i> Time:</strong> <span id="current_time"></span>
                            </div>
                            <button id="refresh_btn" class="refresh-btn">
                                <i class="fa fa-refresh"></i> Refresh Data
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Data Section -->
            <div id="data_section" style="display: none;">
                <!-- Summary Cards -->
                <div class="row" style="margin-bottom: 30px;">
                    <div class="col-md-12">
                        <div id="summary_cards" class="row">
                            <!-- Summary cards will be rendered here -->
                        </div>
                    </div>
                </div>

                <!-- Area Chart Section (Full Width) -->
                <div class="row" style="margin-bottom: 30px;">
                    <div class="col-md-12">
                        <div class="card chart-container">
                            <div class="card-body">
                                <h4 style="text-align: center; color: #2c3e50; margin-bottom: 30px; font-weight: 700;">
                                    <i class="fa fa-area-chart"></i> Cumulative VAT Over Time
                                </h4>
                                <div id="vat_area_chart">
                                    <!-- Area chart will be rendered here -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Chart Section -->
                <div class="row" style="margin-bottom: 30px;">
                    <div class="col-md-12">
                        <div class="card chart-container">
                            <div class="card-body">
                                <h4 style="text-align: center; color: #2c3e50; margin-bottom: 30px; font-weight: 700;">
                                    <i class="fa fa-pie-chart"></i> VAT Distribution by Type
                                </h4>
                                <div id="vat_chart">
                                    <!-- Chart will be rendered here -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Data Table Section -->
                <div class="row">
                    <div class="col-md-12">
                        <div class="card table-card">
                            <div class="card-header"
                                onclick="$('#vat_table_container').slideToggle(300); $('#table_toggle_icon').toggleClass('fa-chevron-down fa-chevron-up');">
                                <h5 style="display: flex; justify-content: space-between; align-items: center;">
                                    <span>
                                        <i class="fa fa-table"></i> VAT Transactions Details
                                    </span>
                                    <i id="table_toggle_icon" class="fa fa-chevron-up"></i>
                                </h5>
                            </div>
                            <div class="card-body" id="vat_table_container" style="display: none; padding: 0;">
                                <div class="table-responsive">
                                    <table id="vat_data_table" class="table table-bordered">
                                        <thead>
                                            <tr>
                                                <th><i class="fa fa-file-text-o"></i> Name</th>
                                                <th><i class="fa fa-calendar"></i> Date</th>
                                                <th><i class="fa fa-university"></i> Tax Account</th>
                                                <th><i class="fa fa-hashtag"></i> Tax ID</th>
                                                <th><i class="fa fa-user"></i> Party</th>
                                                <th><i class="fa fa-money"></i> Tax</th>
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
        let party = $('#party_filter').val();

        if (!company) {
            frappe.msgprint({
                title: __('Missing Information'),
                message: __('Please select a company'),
                indicator: 'orange'
            });
            return;
        }

        if (!from_date || !to_date) {
            frappe.msgprint({
                title: __('Missing Information'),
                message: __('Please select date range'),
                indicator: 'orange'
            });
            return;
        }

        // Update date range display
        $('#date_range_display').text(`${frappe.datetime.str_to_user(from_date)} to ${frappe.datetime.str_to_user(to_date)}`);

        // Show custom loading overlay
        $('body').append(`
            <div class="loading-overlay" id="vat_loading">
                <div class="loading-spinner">
                    <div class="spinner-border"></div>
                    <p style="margin-top: 20px; font-size: 16px; color: #a60f88; font-weight: 600;">
                        <i class="fa fa-spinner fa-spin"></i> Loading VAT Data...
                    </p>
                </div>
            </div>
        `);

        frappe.call({
            method: 'optima_zatca.optima_zatca.page.vat_ledger.vat_ledger.get_vat_ledger_data',
            args: {
                company: company,
                from_date: from_date,
                to_date: to_date,
                tax_account: tax_account,
                party: party
            },
            callback: (r) => {
                $('#vat_loading').remove();
                
                if (r.message) {
                    this.render_data(r.message);
                    $('#data_section').slideDown(400);
                    
                    // Scroll to data section with smooth animation
                    setTimeout(() => {
                        $('html, body').animate({
                            scrollTop: $('#data_section').offset().top - 80
                        }, 600);
                    }, 200);
                    
                    // Show success message
                    frappe.show_alert({
                        message: __('VAT data loaded successfully'),
                        indicator: 'green'
                    }, 3);
                }
            },
            error: () => {
                $('#vat_loading').remove();
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to load VAT data. Please try again.'),
                    indicator: 'red'
                });
            }
        });
    }

    render_data(data) {
        // Render summary cards
        if (data.summary) {
            this.render_summary_cards(data.summary);
        }
        
        // Render area chart - ensure data exists
        if (data.area_chart_data) {
            this.render_area_chart(data.area_chart_data);
        } else {
            console.warn('Area chart data not received');
            $('#vat_area_chart').html(`
                <div class="empty-state">
                    <i class="fa fa-area-chart"></i>
                    <p style="font-size: 16px; margin-top: 15px;">No data available for cumulative chart</p>
                </div>
            `);
        }
        
        // Render chart
        if (data.chart_data) {
            this.render_chart(data.chart_data);
        }
        
        // Render table
        if (data.data) {
            this.render_table(data.data);
        }
    }

    render_summary_cards(summary) {
        const gradients = [
            'linear-gradient(135deg, #400434 0%, #7d0b66 100%)',
            'linear-gradient(135deg, #590649 0%, #a60f88 100%)',
            'linear-gradient(135deg, #7d0b66 0%, #ed95dc 100%)',
            'linear-gradient(135deg, #a60f88 0%, #ed95dc 100%)',
            'linear-gradient(135deg, #400434 0%, #a60f88 100%)',
            'linear-gradient(135deg, #590649 0%, #ed95dc 100%)'
        ];

        const icons = [
            'fa-file-text-o',
            'fa-shopping-cart',
            'fa-exchange',
            'fa-credit-card',
            'fa-calculator',
            'fa-line-chart'
        ];

        let html = '';
        summary.forEach((item, index) => {
            let gradient = gradients[index % gradients.length];
            let icon = icons[index % icons.length];
            
            html += `
                <div class="col-md-4 mb-4">
                    <div class="summary-card-enhanced" style="--card-gradient: ${gradient}">
                        <i class="fa ${icon} summary-card-icon"></i>
                        <div class="summary-card-label">${item.label}</div>
                        <div class="summary-card-value">${format_currency(item.value)}</div>
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <span style="font-size: 12px; color: #6c757d;">
                                <i class="fa ${item.indicator === 'green' ? 'fa-arrow-up' : 'fa-arrow-down'}"></i>
                                ${item.indicator === 'green' ? 'Positive' : 'Negative'}
                            </span>
                            <span style="padding: 4px 12px; background: ${item.indicator === 'green' ? '#d4edda' : '#f8d7da'}; 
                                color: ${item.indicator === 'green' ? '#155724' : '#721c24'}; 
                                border-radius: 20px; font-size: 11px; font-weight: 600;">
                                ${item.indicator === 'green' ? 'Credit' : 'Debit'}
                            </span>
                        </div>
                    </div>
                </div>
            `;
        });
        
        $('#summary_cards').html(html);
    }

    render_area_chart(area_chart_data) {
        console.log('Area Chart Data:', area_chart_data);
        
        if (!area_chart_data || !area_chart_data.labels || !area_chart_data.datasets || 
            area_chart_data.labels.length === 0 || area_chart_data.datasets.length === 0) {
            console.warn('Invalid or empty area chart data');
            $('#vat_area_chart').html(`
                <div class="empty-state">
                    <i class="fa fa-area-chart"></i>
                    <p style="font-size: 16px; margin-top: 15px;">No data available for cumulative chart</p>
                </div>
            `);
            return;
        }

        // Validate and sanitize data - ensure all values are valid numbers
        try {
            const sanitizedDatasets = area_chart_data.datasets.map(dataset => {
                return {
                    name: dataset.name,
                    values: dataset.values.map(v => {
                        const num = parseFloat(v);
                        return isNaN(num) || !isFinite(num) ? 0 : num;
                    })
                };
            });
            
            // Validate labels
            if (area_chart_data.labels.some(label => !label)) {
                throw new Error('Invalid labels detected');
            }
            
            // Validate all datasets have same length as labels
            const labelCount = area_chart_data.labels.length;
            for (const dataset of sanitizedDatasets) {
                if (dataset.values.length !== labelCount) {
                    throw new Error(`Dataset "${dataset.name}" length mismatch`);
                }
            }

            // Clear previous chart
            $('#vat_area_chart').html('');

            // Add a small delay to ensure DOM is ready and previous chart is destroyed
            setTimeout(() => {
                try {
                    new frappe.Chart('#vat_area_chart', {
                        data: {
                            labels: area_chart_data.labels,
                            datasets: sanitizedDatasets
                        },
                        type: 'axis-mixed',
                        height: 350,
                        colors: ['#590649', '#ed95dc', '#a60f88'],
                        lineOptions: {
                            regionFill: 1,
                            dotSize: 6,
                            hideLine: 0,
                            hideDots: 0,
                            heatline: 0,
                            spline: 1
                        },
                        axisOptions: {
                            xAxisMode: 'tick',
                            xIsSeries: 1
                        }
                    });
                } catch (chartError) {
                    console.error('Chart creation error:', chartError);
                    $('#vat_area_chart').html(`
                        <div class="empty-state">
                            <i class="fa fa-exclamation-triangle"></i>
                            <p style="font-size: 16px; margin-top: 15px;">Error creating chart: ${chartError.message}</p>
                        </div>
                    `);
                }
            }, 150);
        } catch (error) {
            console.error('Error rendering area chart:', error);
            $('#vat_area_chart').html(`
                <div class="empty-state">
                    <i class="fa fa-exclamation-triangle"></i>
                    <p style="font-size: 16px; margin-top: 15px;">Error rendering chart: ${error.message}</p>
                </div>
            `);
        }
    }

    render_chart(chart_data) {
        if (!chart_data || !chart_data.labels || chart_data.labels.length === 0) {
            $('#vat_chart').html(`
                <div class="empty-state">
                    <i class="fa fa-pie-chart"></i>
                    <p style="font-size: 16px; margin-top: 15px;">No data available for chart visualization</p>
                </div>
            `);
            return;
        }

        // Clear previous chart
        $('#vat_chart').html('');

        new frappe.Chart('#vat_chart', {
            data: {
                labels: chart_data.labels,
                datasets: [{
                    values: chart_data.values
                }]
            },
            type: 'donut',
            height: 350,
            colors: ['#3b0734', '#9e0389']
        });
    }

    render_table(data) {
        let tbody = $('#vat_data_table tbody');
        tbody.empty();

        if (!data || data.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="6">
                        <div class="empty-state">
                            <i class="fa fa-database"></i>
                            <p style="font-size: 16px; margin-top: 15px;">No transaction data found for the selected period</p>
                        </div>
                    </td>
                </tr>
            `);
            return;
        }

        data.forEach(row => {
            // Check if it's a header row
            if (row.name && row.name.includes('<h5')) {
                let headerText = $(row.name).text();
                tbody.append(`
                    <tr class="group-header-row no-hover">
                        <td colspan="6">
                            <i class="fa fa-folder-open"></i> ${headerText}
                        </td>
                    </tr>
                `);
            }
            // Skip total rows
            else if (row.name && row.name.includes('Total')) {
                // Do nothing - skip total rows
            }
            // Check if it's an empty row
            else if (!row.name && !row.base_tax_amount) {
                // Skip empty rows as well
            }
            // Regular data row
            else {
                let name_link = row.name;
                if (row.parenttype && row.name) {
                    name_link = `<a href="/app/${row.parenttype.toLowerCase().replace(/ /g, '-')}/${row.name}" 
                        target="_blank" style="color: #a60f88; font-weight: 600; text-decoration: none;">
                        <i class="fa fa-external-link" style="font-size: 10px;"></i> ${row.name}
                    </a>`;
                }
                
                let amount_color = row.base_tax_amount >= 0 ? '#28a745' : '#dc3545';
                
                tbody.append(`
                    <tr>
                        <td>${name_link}</td>
                        <td><i class="fa fa-calendar-o"></i> ${frappe.datetime.str_to_user(row.posting_date) || ''}</td>
                        <td style="font-size: 13px;">${row.tax_account || ''}</td>
                        <td><span style="color: #6c757d; font-family: monospace;">${row.tax_id || '-'}</span></td>
                        <td style="font-weight: 500;">${row.party || ''}</td>
                        <td class="text-right" style="font-weight: 600; color: ${amount_color};">
                            ${format_currency(row.base_tax_amount || 0)}
                        </td>
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
