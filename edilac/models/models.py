from odoo.exceptions import UserError

from odoo import models, fields, api,_


class H_Purchase(models.Model):
    _name = 'purchase.order'
    _inherit = 'purchase.order'
    _description = 'Description'

    state = fields.Selection([
        ('draft', 'Demande de prix'),
        ('sent', 'Envoyé'),
        ('submit', "En attente de validation"),
        ('approved', "En attente d'approbation"),
        ('to approve', 'A approuver'),
        ('purchase', 'Bon de commande'),
        ('done', 'Bloqué'),
        ('cancel', 'Annulé')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    vat = fields.Html(string='Vat', required=False)
    type = fields.Selection(
        string=_('type'),
        selection=[
            ('local', 'local'),
            ('import', 'Import'),
        ], default='local'
    )


    # mail_dg = fields.Char(string='mail', required=False, default='alexandre@gmail.com')

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.browse()
        partner_vals_list = []
        for vals in vals_list:
            # Vérifiez si la commande a des lignes
            if 'order_line' not in vals or not vals['order_line']:
                raise UserError("Vous ne pouvez pas créer une commande d'achat sans lignes de commande.")

            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            # Assurez-vous que le type de prélèvement et la devise par défaut sont pris dans la bonne entreprise.
            self_comp = self.with_company(company_id)
            if vals.get('name', 'New') == 'New':
                seq_date = None
                if 'date_order' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
                vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.order',
                                                                         sequence_date=seq_date) or '/'
            vals, partner_vals = self._write_partner_values(vals)
            partner_vals_list.append(partner_vals)
            orders |= super(H_Purchase, self_comp).create(vals)
        for order, partner_vals in zip(orders, partner_vals_list):
            if partner_vals:
                order.sudo().write(
                    partner_vals)  # Parce que l'utilisateur d'achat n'a pas le droit d'écriture sur `res.partner`
        return orders

    def button_action_submit(self):
        for rec in self:
            rec.state = 'submit'

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent', 'submit']:
                continue
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'purchase'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True

    def button_action_approuve_daf(self):
        check_config = self.env['res.config.settings'].search([], limit=1)
        print(check_config)
        self.write({'state': 'approved'})
        for rec in self:
            rec.button_confirm()

    def action_submit(self):
        return self.send_email()

    def button_confirm_test(self):
        for order in self:
            if order.state != 'approved':
                raise UserError("L'état de la commande doit être 'approved' pour être confirmée.")
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'purchase'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True

