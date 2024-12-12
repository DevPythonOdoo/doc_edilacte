# -*- coding: utf-8 -*-
import logging
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)



class InactiveCustomersWizard(models.TransientModel):
    _name = 'customers.wizard'
    _description = 'Inactive Customers Wizard'

    start_date = fields.Date(string="Date début",default=lambda *a: time.strftime('%Y-%m-01'), required=True)
    end_date = fields.Date(string="Date Fin", required=True,default=lambda *a: str(
        datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    area_id = fields.Many2one(comodel_name='area.area', string='Zone')
    common_id = fields.Many2one(comodel_name='common.common', string='Commune')
    


    def generate_report(self):
        """Rechercher les clients inactifs et générer un rapport PDF."""
        self.ensure_one()
        
        
        
        # raise UserError(domain)
        orders = self.env['sale.order'].search([('date_order', '>=', self.start_date), ('date_order', '<=', self.end_date),('state', 'in', ['sale', 'done'])])
        # raise UserError("%s et %s"%(orders,domain))

        active_customers = orders.mapped('partner_id.id')
        domain = [('id', 'not in', active_customers),('customer_rank', '>', 0)]
       

        if self.area_id and not self.common_id:
            domain.append(('area_id', '=', self.area_id.id))
        
        if self.area_id and  self.common_id:
            domain.append(('common_id', '=', self.common_id.id))

        # Rechercher les clients qui n'ont pas passé de commande
        inactive_customers = self.env['res.partner'].search(domain)

        # raise UserError(inactive_customers)
        if not inactive_customers:
            raise UserError(_('Aucun client inactif trouvé sur la période.'))
        
        # Créer un rapport PDF
        report_data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'customers': inactive_customers,
            
        }
        return self.env.ref('edilac.report_customers_wizards').with_context(landscape=True).report_action(self, data=report_data)
