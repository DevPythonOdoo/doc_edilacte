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
        ('to approve', 'A approuver'),
        ('purchase', 'Bon de commande'),
        ('done', 'Bloqué'),
        ('cancel', 'Annulé')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

    # vat = fields.Html(string='Vat', required=False)

    number_palet = fields.Float(string='Nombre Totale de Palet',compute='_compute_total_palet',required=False, store= True)
    qte_palet = fields.Float(string='Total Palet',required=False,  compute='_compute_total', store=True)
    product_qty = fields.Float(string='Total',required=False,  compute='_compute_total', store=True)
    company_currency_id = fields.Many2one('res.currency', string='Devise societé', required=True, default=lambda self: self.env.company.currency_id)
    total_amount_devise = fields.Monetary(string='Total FCFA', required=False, currency_field="company_currency_id", compute='_compute_total_amount_devise', store=True)
    
    @api.depends('order_line')
    def _compute_total(self):
        for order in self:
            order.product_qty = sum(line.product_qty for line in order.order_line)
            order.qte_palet = sum(line.qte_palet for line in order.order_line)

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
   

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.browse()
        partner_vals_list = []
        for vals in vals_list:
            # Vérifiez si la commande a des lignes
            # if 'order_line' not in vals or not vals['order_line']:
            #     raise UserError("Vous ne pouvez pas créer une commande d'achat sans lignes de commande.")

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
            if order.type == "import":
                order.write({'state': 'to approve'})
            else:
                order.button_approve()
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True


    def button_action_validate(self):
        return self.button_confirm()

    def button_approve(self):
        # Appelez la méthode de confirmation de base
        super(Purchase, self).button_approve()
        
        for order in self:
            # Initialiser le compteur pour chaque commande
            lot_counter = 1
            
            # Récupérer la référence fournisseur
            supplier_ref = order.partner_ref or 'REF'
            po_ref = order.name or 'BCI'
            
            # Chercher les réceptions liées à cette ligne de commande 
            stock_pickings = self.env['stock.picking'].search([
                ('origin', '=', order.name),
                ('state', 'not in', ('done', 'cancel'))  # Filtrer les réceptions en attente ou confirmées
            ])

            # Mettre à jour le champ `origin` des réceptions avec la concaténation de la référence PO  =et la référence fournisseur
            origin = None
            for picking in stock_pickings:
                picking.origin = f"{po_ref} - {supplier_ref}" if po_ref and supplier_ref else po_ref
                origin = picking.origin
                    
            for line in order.order_line:
               
                # Chercher les réceptions liées à cette ligne de commande
                stock_moves = self.env['stock.move'].search([
                    ('purchase_line_id', '=', line.id),
                    ('state', 'not in', ('done', 'cancel'))  # Uniquement les mouvements en attente
                ])
                # Vérifier si le produit n'est pas un congélilateur
                if not line.product_id.freezer and order.type =="import" :
                # Générer les numéros de lot pour chaque mouvement de stock
                    for move in stock_moves:
                        # Créer un numéro de lot incrémenté
                        lot_name = f"{supplier_ref}-{str(lot_counter).zfill(3)}"
                        
                        # Créer le lot
                        lot = self.env['stock.lot'].create({
                            'name': lot_name,
                            'product_qty': line.product_qty,
                            'ref': origin,
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
    
    
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qte_palet = fields.Float(string='Palet/Qte', required=False)
    type = fields.Selection(
        string=_('type'),
        selection=[
            ('local', 'local'),
            ('import', 'Import'),
        ], related="order_id.type"
    )

    @api.onchange('qte_palet', 'product_qty')
    def _onchange_product_qte(self):
        for line in self:
            product = line.product_id.product_tmpl_id
            # line.qte_palet = 0
            if line.qte_palet:  
                line.product_qty = line.qte_palet * product.palet * product.uom_id.ratio
            

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    palet = fields.Integer('Nbre de carton en palette', default=1,  help="Cette valeur sera utilisé pour obtenir le nombre de carton pour une commande fournisseur de ce produit")
    freezer = fields.Boolean(string='Marqué Comme un Congélateur', required=False, help="Une fois coché le produit sera marqué comme un congélateur")


