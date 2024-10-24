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
    'depends': ['base', 'product', 'purchase', 'stock', 'sale', 'account', 'crm','contacts','sales_team'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/purchase_order.xml',
        'views/sequence_views.xml',
        'views/salesperson.xml',
        'views/partner.xml',
        'views/stock.xml',
        'views/product_available.xml',
        #'report/purchase_order_template.xml',  # Corrected typo in filename
        'report/stock_template.xml',
    ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'license': 'LGPL-3',
}
