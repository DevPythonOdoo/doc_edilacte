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


    # any module necessary for this one to work correctly
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase', 'stock', 'sale', 'account', 'crm'],

    # always loaded
    'data': [
<<<<<<< HEAD
        # 'security/ir.model.access.csv',
        'views/purchase_order.xml',
=======
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/models.xml',
>>>>>>> 463a10589005e7aa087aab54d76943835311826e

        'report/purchase_oder_template.xml',

<<<<<<< HEAD
        #'views/templates.xml',
=======
        'views/templates.xml',
        'views/partner.xml',
>>>>>>> 463a10589005e7aa087aab54d76943835311826e
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'license': 'LGPL-3'

}
