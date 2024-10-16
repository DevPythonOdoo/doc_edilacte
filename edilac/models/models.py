from odoo.exceptions import UserError

from odoo import models, fields, api,_, tools


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

    number_palet = fields.Integer(string='Nombre Totale de Palet',compute='_compute_total_palet',required=False, store= True)
    qte_palet = fields.Integer(string='Total Palet',required=False, store= True,related='order_line.qte_palet')
    product_qty = fields.Float(string='Total Carton',required=False, store= True, related='order_line.product_qty')

    type = fields.Selection(
        string=_('type'),
        selection=[
            ('local', 'local'),
            ('import', 'Import'),
        ], default='local'
    )


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


    @api.model_create_multi
    def create(self, vals_list):
        orders = self.browse()
        partner_vals_list = []

        for vals in vals_list:
            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            self_comp = self.with_company(company_id)

            # Vérifier si le nom de la commande est 'New' pour générer un numéro
            if vals.get('name', 'New') == 'New':
                seq_date = None
                if 'date_order' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))

                # Mettre à jour le préfixe de la séquence si nécessaire
                try:
                    sequence = self_comp.env.ref('purchase.seq_purchase_order', raise_if_not_found=True)
                    # Mise à jour du préfixe
                    sequence.sudo().write({
                        'prefix': 'BC',
                        'padding': 5,  # Exemple de padding
                    })

                    # Génération du numéro de commande
                    vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.order',
                                                                             sequence_date=seq_date) or '/'
                except Exception:
                    vals['name'] = '/'  # Valeur par défaut en cas d'erreur

            # Écriture des valeurs partenaires
            vals, partner_vals = self._write_partner_values(vals)
            partner_vals_list.append(partner_vals)

            # Création de la commande
            orders |= super(H_Purchase, self_comp).create(vals)

        # Mise à jour des valeurs partenaires après la création des commandes
        for order, partner_vals in zip(orders, partner_vals_list):
            if partner_vals:
                order.sudo().write(
                    partner_vals)  # Les utilisateurs d'achats n'ont pas de droits d'écriture sur `res.partner`

        return orders
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qte_palet = fields.Integer(string='Palet/Qte', required=False, readonly=False, store=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=False)

    @api.onchange('product_id', 'product_qty')
    def _onchange_product_qty(self):
        for line in self:
            product = line.product_id.product_tmpl_id
            if line.product_qty:  # Vérifier si la quantité est renseignée
                if product.uom_palet_id:
                    # Utiliser uom_palet_id pour le calcul si disponible
                    line.qte_palet = line.product_qty / product.uom_palet_id
                elif product.uom_conteneur_id:
                    # Sinon, utiliser uom_conteneur_id s'il est renseigné
                    line.qte_palet = line.product_qty / product.uom_conteneur_id
                else:
                    # Aucun des deux n'est renseigné, mettre qte_palet à 0
                    line.qte_palet = 0
            else:
                # Si la quantité n'est pas renseignée, mettre qte_palet à 0
                line.qte_palet = 0


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    uom_palet_id = fields.Integer('Mesure en Palet', required=False, help="Default unit of measure used for purchase orders.",store=True)
    uom_conteneur_id = fields.Integer('Mesure en Conteneur', required=False, help="Default unit of measure used for purchase orders.",store=True)
    purchase_id = fields.One2many(comodel_name='purchase.order.line', inverse_name='product_id', string='Purchase Orders', required=False)



