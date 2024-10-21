from odoo.exceptions import UserError

from odoo import models, fields, api,_, tools


from odoo import models, fields, api,_


class Purchase(models.Model):
    _name = 'purchase.order'
    _inherit = 'purchase.order'
    _description = 'Description'

    type = fields.Selection(
        string=_('type'),
        selection=[
            ('local', 'local'),
            ('import', 'Import'),
        ], default='local'
    )
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

    # vat = fields.Html(string='Vat', required=False)

    number_palet = fields.Integer(string='Nombre Totale de Palet',compute='_compute_total_palet',required=False, store= True)
    qte_palet = fields.Integer(string='Total Palet',required=False,  related="order_line.qte_palet", store=True)
    product_qty = fields.Float(string='Total Carton',required=False,  related="order_line.product_qty", store=True)
    company_currency_id = fields.Many2one('res.currency', string='Devise societé', required=True, default=lambda self: self.env.company.currency_id)
    total_amount_devise = fields.Monetary(string='Total FCFA', required=False, currency_field="company_currency_id", compute='_compute_total_amount_devise', store=True)
    


    @api.depends('partner_id', 'amount_total', 'currency_id')
    def _compute_total_amount_devise(self):
        for order in self:
            # Initialisation du montant à zéro
            order.total_amount_devise = 0.0
            # Vérification que le partenaire a une liste de prix
            if order.partner_id and order.currency_id:
                order.total_amount_devise = order.amount_total * order.currency_id.rate


    @api.depends('order_line.qte_palet')
    def _compute_total_palet(self):
        for order in self:
            total_palet = sum(line.qte_palet for line in order.order_line)
            order.number_palet = total_palet
    # mail_dg = fields.Char(string='mail', required=False, default='alexandre@gmail.com')


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
                if vals.get('type') == 'import':
                    # raise UserError(self.env['ir.sequence'].next_by_code('purchase.import'))
                    vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.import',sequence_date=seq_date)
                else:
                    vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.order',sequence_date=seq_date) or '/'
            vals, partner_vals = self._write_partner_values(vals)
            partner_vals_list.append(partner_vals)
            orders |= super(Purchase, self_comp).create(vals)
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
        for rec in self:
            # Vérifiez le type de l'enregistrement
            if rec.type == 'local':
                # Si le type est 'local', passez à 'purchase'
                rec.write({'state': 'purchase'})
            elif rec.type == 'import':
                # Si le type est 'import', passez à 'approved' et confirmez
                rec.write({'state': 'approved'})
                rec.button_confirm()



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



class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qte_palet = fields.Integer(string='Palet/Qte', required=False)
    type = fields.Selection(
        string=_('type'),
        selection=[
            ('local', 'local'),
            ('import', 'Import'),
        ], related="order_id.type"
    )

    @api.onchange('qte_palet', 'product_qty')
    def _onchange_product_qty(self):
        for line in self:
            product = line.product_id.product_tmpl_id
            # line.qte_palet = 0
            if line.qte_palet:  
                line.product_qty = line.qte_palet * product.palet
            



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    palet = fields.Integer('Nbre de carton en palette', default=1,  help="Cette valeur sera utilisé pour obtenir le nombre de carton pour une commande fournisseur de ce produit")
    # uom_conteneur_id = fields.Integer('Mesure en Conteneur', required=False, help="Default unit of measure used for purchase orders.",store=True)


class ResUsers(models.Model):
    _inherit = 'res.users'

    as_a_salesperson = fields.Boolean('Comme un commercial')
    invoiced_target = fields.Float(string="Objectif de facturation")

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    @api.model
    def write(self, vals):
        # Sauvegarder les utilisateurs actuels avant la mise à jour
        previous_members = self.member_ids
        # Appeler la méthode write pour effectuer la mise à jour
        res = super(CrmTeam, self).write(vals)
        # Récupérer les nouveaux membres après la mise à jour
        current_members = self.member_ids
        # Activer as_a_salesperson pour les utilisateurs ajoutés
        for user in current_members:
            if user not in previous_members:
                user.as_a_salesperson = True
        # Désactiver as_a_salesperson pour les utilisateurs supprimés
        for user in previous_members:
            if user not in current_members:
                user.as_a_salesperson = False

        return res


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('parent_id')
    def _compute_team_id(self):
        for partner in self.filtered(lambda p: not p.team_id and p.company_type == 'person' and p.parent_id.team_id):
            # Vérifiez si l'équipe parent a au moins un commercial actif
            if partner.parent_id.team_id.has_salesperson:
                partner.team_id = partner.parent_id.team_id