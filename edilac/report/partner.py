from datetime import datetime
from odoo import api, models,exceptions
from odoo.http import request


class CustomerQrTemplate(models.AbstractModel):
    """Abstract model for generating the customer QR template report."""
    _name = 'report.edilac.freezer_qr_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Get the report values for generating the customer QR template."""
        if data['type'] == 'cust':
            dat = [request.env['freezer.assignment'].browse(data['data'])]
        
        return {'data': dat}

class CustomerWizard(models.AbstractModel):
    _name = 'report.edilac.report_customers_wizard_views'

    @api.model
    def _get_report_values(self, docids, data=None):
        if 'res.partner(' in data['customers']:
            ids_str = data['customers'].split('(')[1].split(')')[0]  # Récupérer la partie entre ()
            customer_ids = [int(x.strip()) for x in ids_str.split(',')]  # Transformer en liste d'entiers

        # Convertir la chaîne en objet datetime
        start_datetime = datetime.strptime(data['start_date'], '%Y-%m-%d')
        end_datetime = datetime.strptime( data['end_date'], '%Y-%m-%d')
        
        # Convertir en objet date

        start = start_datetime.date().strftime('%d %B %Y')
        end = end_datetime.date().strftime('%d %B %Y')
        
        return {
            'doc_ids': docids,
            'doc_model': 'customers.wizard',
            'docs': self.env['res.partner'].browse(customer_ids),
            'data': data,
            'start': start,
            'end': end,

        }