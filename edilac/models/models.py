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
        # Appelez la méthode de confirmation de base
        super(Purchase, self).button_confirm()

        for order in self:
            # Initialiser le compteur pour chaque commande
            lot_counter = 1

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

            for line in order.order_line:
                # Récupérer la référence fournisseur
                supplier_ref = order.partner_ref or 'REF'
                
                # Chercher les réceptions liées à cette ligne de commande
                stock_moves = self.env['stock.move'].search([
                    ('purchase_line_id', '=', line.id),
                    ('state', 'not in', ('done', 'cancel'))  # Uniquement les mouvements en attente
                ])

                # Générer les numéros de lot pour chaque mouvement de stock
                for move in stock_moves:
                    # Créer un numéro de lot incrémenté
                    lot_name = f"{supplier_ref}-{str(lot_counter).zfill(3)}"
                    
                    # Créer le lot
                    lot = self.env['stock.lot'].create({
                        'name': lot_name,
                        'product_qty': line.product_qty,
                        'product_id': line.product_id.id,
                        'location_id': move.location_id.id,
                        #'location_dest_id': move.location_dest_id.id,
                        'company_id': order.company_id.id,
                    })
                    
                    # Associer le lot au niveau des lignes de mouvement de stock (stock.move.line)
                    move_line = self.env['stock.move.line'].search([('move_id', '=', move.id)], limit=1)
                    if move_line:
                        move_line.write({
                            'lot_id': lot.id,
                            'lot_name': lot.name,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                        })
                    move.write({'lot_ids': [(4, lot.id)]})
                    # Incrémenter le compteur pour le prochain lot
                    lot_counter += 1      
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

    invoiced_target = fields.Monetary(string="Objectif de facturation")

    invoiced_target = fields.Float(string="Objectif de facturation")
    target_ids = fields.One2many(
        string=_('Objectifs Commercial'),
        comodel_name='saleman.line',
        inverse_name='user_id',
    )
    customers_ids = fields.One2many(
        string=_('Clients suivi'),
        comodel_name='res.partner',
        inverse_name='user_id',
    )

class SalemLine(models.Model):
    _name = 'saleman.line'
    _description = _('Objectif Commercial')
    
    date_start = fields.Date(string="Date début",required=True)
    date_end = fields.Date(string="Date fin",required=True)
    target_amount = fields.Monetary(string="Montant objectif")
    currency_id = fields.Many2one('res.currency', string="Devise",default=lambda self: self.env.company.currency_id)
    real_amount = fields.Monetary(string="Montant réel",compute='_compute_real_amount',store=True)
    percentage = fields.Float(string="Pourcentage d'atteinte",compiled=True, store=True, compute='_compute_percentage')
    user_id = fields.Many2one('res.users', string="Commercial")
    line_ids = fields.One2many(
        string=_('Commande Client'),
        comodel_name='sale.order',
        inverse_name='user_id',
    )

    def _compute_percentage(self):
        for record in self:
            record.percentage = (record.real_amount / record.target_amount) * 100 if record.target_amount else 0.0
    def _compute_real_amount(self):
        for record in self:
            record.real_amount = sum(order.amount_total for order in record.line_ids if order.state in ('sale','done'))



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





class SaleOrder(models.Model):
    _inherit = 'sale.order'

    region_id = fields.Many2one(comodel_name='region.region', string='Region',related="partner_id.region_id",store=True)
    city_id = fields.Many2one(comodel_name='city.city',string='Ville',related="partner_id.city_id",store=True)
    area_id = fields.Many2one(comodel_name='area.area',string='Zone',related="partner_id.area_id",store=True)
    common_id = fields.Many2one(comodel_name='common.common',string='Commune',related="partner_id.common_id",store=True)
    family_cust = fields.Many2one(comodel_name='family.custom',string='Famille client',related="partner_id.family_cust",store=True)
    neighborhood_id = fields.Many2one(comodel_name='neighborhood.neighborhood',string='Quartier',related="partner_id.neighborhood_id",store=True)
    @api.model
    def create(self, vals):
        # Récupérer le partenaire et son type de client
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        prefix = 'S'  # Préfixe par défaut

        # Modifier le préfixe en fonction du type de client
        if partner.customer_type == 'tva':
            prefix = 'T'
        elif partner.customer_type == 'normal':
            prefix = 'N'
        elif partner.customer_type == 'normal_d':
            prefix = 'ND'

        # Générer le numéro de séquence en utilisant le préfixe personnalisé
        seq = self.env['ir.sequence'].next_by_code('sale.order') or '/'
        vals['name'] = prefix + seq[1:]  # Remplace le premier caractère par le préfixe désiré

        # Appeler la méthode create parente
        return super(SaleOrder, self).create(vals)
    
    from odoo import models, fields, api, _
    
    
class saleOderLine(models.Model):
    _inherit = 'sale.order.line'

    date_order = fields.Datetime(string=_('Date Commande'), related='order_id.date_order',store=True,precompute=True)
    partner_type = fields.Selection(related='order_partner_id.customer_type', string=_('Type de client'),store=True,precompute=True)
    invoice_status = fields.Selection(related='order_id.invoice_status', string=_('Etat de facturation'),store=True,precompute=True)
    
    