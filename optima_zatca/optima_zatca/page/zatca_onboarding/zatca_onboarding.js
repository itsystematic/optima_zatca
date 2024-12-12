frappe.pages['zatca-onboarding'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '',
        single_column: true,
    });

    $('#body').append('<div id="root"></div>');
    $('header').remove();
    $('.content.page-container').remove()

    frappe.require('/assets/optima_zatca/zatca-onboarding/zatca_onboarding.js', () => {
        console.log('React online');
        $('link[rel="stylesheet"][href*="desk.bundle"]').remove();
    })



    frappe.router.on('change',  () => {
        window.location.reload();
    });


};
