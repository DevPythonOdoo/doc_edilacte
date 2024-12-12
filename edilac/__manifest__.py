# -*- coding: utf-8 -*-
{
    'name': "edilacte",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "ADG",
    'website': "https://www.adg.ci",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'purchase', 'stock', 'sale', 'account', 'crm', 'contacts', 'sales_team', 'fleet',
                'stock_picking_batch', 'mail', 'account_followup','web'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/assignment.xml',
        "wizard/freezer_paiement_wz.xml",
        'views/purchase_order.xml',
        'views/sequence_views.xml',
        'views/salesperson.xml',
        'views/partner.xml',
        'views/stock.xml',
        'views/freezer_assignment.xml',
        'views/field_visit.xml',
        'views/delivery_person.xml',
        'report/report_purchaseorder_import.xml',
        'report/report_quotation_import.xml',
        'report/report_bon_prepa.xml',
        'report/report_bon_commande.xml',
        'report/report_preparation.xml',
        'report/report_bl.xml',
        'report/stock_template.xml',
        'data/mail_template_adv.xml',
        'data/mail_template_depoiement.xml',
        "wizard/partner.xml",
        "report/customers_wizard_report.xml",
        "report/freezer_qrcode.xml",

    ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    "assets": {
        "web.assets_backend": [
            'edilac/static/js/field_visit_geo.js',
            'edilac/static/src/js/field_visit_geo.js',
            'edilac/static/src/lib/ZXing.js',
            'edilac/static/src/js/field_visit_barcode_mobile.js',

        ],
       
    },

    'license': 'LGPL-3',
}
