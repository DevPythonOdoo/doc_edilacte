import time
from odoo import models, fields, api,_
from odoo.exceptions import UserError
from collections import defaultdict

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_datetime, format_date, groupby


class StockMove(models.Model):
    _inherit = 'stock.move'

    gaps = fields.Float(string="ecart", default=0.00, copy=False)  
    quality_id = fields.Many2one(comodel_name='quality.quality',string='Qualité')  
    false_product_uom_qty = fields.Float('Quantités commandées', default=0.00, )
    manual_tranfert_move = fields.Boolean(string='Transfert manuel', default=False)
    amount_collected = fields.Monetary(string="Montant encaissé",compute="compute_price_unit", readonly=True)
    price_total = fields.Monetary(string="Montant commande", compute="compute_price_unit", readonly=True)
    currency_id = fields.Many2one('res.currency', 'Devise', default=lambda self: self.env.company.currency_id,
                                  readonly=True, required=True)
    picking_step = fields.Selection(related='picking_id.picking_type_id.step', readonly=True)
    moveline_id = fields.Many2one('stock.move.line', 'Stock line',)
    # product_lot_id = fields.Many2one('stock.lot',string='lot', compute="check_lot")
    
    
    @api.depends('move_line_ids.lot_id')
    def check_lot(self):
        for rec in self:  
            for line in rec.move_line_ids:
            
                self.product_lot_id = line.lot_id if rec.product_id == line.product_id and line.lot_id else False
 
    @api.depends('picking_id.sale_id.order_line')
    def compute_price_unit(self):
        for rec in self:
            # Initialiser les valeurs par défaut
            rec.price_total = 0.0
            rec.amount_collected = 0.0
            # Vérifier si un picking ou une vente est lié
            if rec.picking_id and rec.picking_id.sale_id:
                for line in rec.picking_id.sale_id.order_line:
                    if line.product_id == rec.product_id:
                        rec.price_total = line.price_total
                        price_unit_ht = line.price_unit
                        qty = rec.quantity
                        taxes = line.tax_id.compute_all(price_unit_ht, rec.picking_id.sale_id.currency_id, qty, product=line.product_id, partner=rec.picking_id.sale_id.partner_id)
                        rec.amount_collected = taxes['total_included'] if taxes else price_unit_ht * qty
  
                        break  # Sortir de la boucle après avoir trouvé une correspondance 
        
            
    @api.onchange('quantity', 'product_uom_qty')
    def _compute_ecart(self):
        for rec in self:
            if rec.quantity and rec.product_uom_qty:
                rec.gaps = rec.product_uom_qty - rec.quantity
            if rec.quantity ==0:    
                rec.gaps = rec.product_uom_qty - 0
                #rec.false_product_uom_qty = rec.quantity
            if rec.picking_code == 'internal' and rec.manual_tranfert_move:   
                quantity_requested = rec.product_uom_qty
                available_quantity = rec.product_id.with_context({'location': rec.location_id.id}).qty_available

                # Vérification si la quantité demandée est supérieure à la quantité disponible
                if quantity_requested > available_quantity:
                    raise UserError(_(
                        "La quantité à déplacer pour le produit %s est supérieure au stock actuel. "
                        "Vous avez seulement %s produits en stock dans l'emplacement %s."
                    ) % (rec.product_id.display_name, available_quantity, rec.location_id.display_name))
     
class Stock(models.Model):
    _inherit = 'stock.picking'

    total_ordered = fields.Float(string="Total commandé",default=0.00, compute='_cumul_total_sum', store=True, readonly=True)
    total_received = fields.Float(string="Total reçu", default=0.00, compute='_cumul_total_sum', store=True, readonly=True)
    total_ecart = fields.Float(string="Total ecart",default=0.00, compute='_cumul_total_sum', store=True, readonly=True)    
    manual_tranfert = fields.Boolean(string='Transfert manuel', default=False)
    type_code = fields.Char(string="Code Type Picking (première ligne)",compute="_cumul_total_sum", store=True)
    region_id = fields.Many2one('region.region', string="Région", related="partner_id.region_id")
    city_id = fields.Many2one('city.city', string="Ville", related="partner_id.city_id")
    area_id = fields.Many2one('area.area', string="Zone", related="partner_id.area_id")
    common_id = fields.Many2one('common.common', string="Commune", related="partner_id.common_id")
    neighborhood_id = fields.Many2one('neighborhood.neighborhood', string="Quartier", related="partner_id.neighborhood_id")
    #delivery_ids = fields.One2many(comodel_name='delivery.delivery', inverse_name="picking_id", string='Livraison')
    assignment_id = fields.Many2one('assignment.assignment', string="Livraison", required=False)
    agent_id = fields.Many2one("delivery.person",string="livreur",related="assignment_id.delivery_agent_id", store=True,copy=True)
    #user_id = fields.Many2one("res.users",string="livreur",related="agent_id.name", store=True)
    user_id = fields.Many2one(
    'res.users', 'Responsible', tracking=True,copy=True,
    domain=lambda self: [('groups_id', 'in', self.env.ref('stock.group_stock_user').id)],
    default=lambda self: self.env.user)
    batch_id = fields.Many2one(comodel_name='stock.picking.batch')
    fleet_vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehicule', related="batch_id.fleet_vehicle_id",copy=True)
    sale_id = fields.Many2one(comodel_name='sale.order', string='Vente')
    #return_id = fields.Many2one(comodel_name='stock.return.picking', string='Retour')
    status = fields.Selection(
        string=_('status'),
        selection=[
            ('draft', 'Nouvelle Commande'),
            ('done', 'Commande Validé'),
        ],default="draft",
    )
    state_assignement = fields.Selection(
        string=_("statut d'affectation"),
        selection=[
            ('draft', 'Non affectée'),
            ('assigned', 'Affectée'),
        ],default="draft",
    )
    state_deliv = fields.Selection(
        string=_('statut livraison'),
        selection=[
            ('done', 'Livré'),
            ('cancel', 'Annuler'),
        ],default="done",
    )
    comment = fields.Text(string="Description")
    picking_step_stk = fields.Selection(related='picking_type_id.step', readonly=True)
   
   
    # def button_validate(self):  
    #     for rec in self:
    #          # Appelez la méthode de confirmation de base
    #         super(Stock, self).button_validate()
            
    #         rec.state_assignement = "assigned"
    #         rec.user_id = rec.batch_id.user_id.id
        
    #         rec.state_assignement = "assigned"
    #         rec.user_id = rec.batch_id.user_id.id
            
        
        
    def update(self):
        for rec in self:
            if rec.type_code == 'internal' and not rec.manual_tranfert:
                rec.manual_tranfert = True
                rec.move_ids_without_package.manual_tranfert_move = True

    def do_validate_order(self):
        for rec in self:
            rec.status = "done"           
    
    @api.model
    def create(self, vals):
        record = super(Stock, self).create(vals)
        record.update()   
        return record
    
    @api.depends('move_ids_without_package')
    def _cumul_total_sum(self):
        for rec in self:
            rec.total_ordered = 0
            rec.total_received = 0
            rec.total_ecart = 0
            if rec.move_ids_without_package:
                rec.total_ordered = sum(rec.move_ids_without_package.mapped('product_uom_qty'))
                rec.total_received = sum(rec.move_ids_without_package.mapped('quantity'))
                rec.total_ecart = sum(rec.move_ids_without_package.mapped('gaps'))
                # Récupère le code du picking_type_id de la première ligne d'opération
                rec.type_code = rec.move_ids_without_package[0].picking_type_id.code
            else:
                rec.type_code = " "   

           
    @api.onchange('move_ids_without_package')
    def check_stock_availability(self):
        """ Vérification de la disponibilité du stock pour chaque mouvement avant la confirmation du picking. """
        for picking in self:
            if picking.type_code == 'internal' and picking.manual_tranfert:
                for move in picking.move_ids_without_package:
                    quantity_requested = move.product_uom_qty
                    available_quantity = move.product_id.with_context({'location': move.location_id.id}).qty_available

                    # Vérification si la quantité demandée est supérieure à la quantité disponible
                    if quantity_requested > available_quantity:
                        raise UserError(_(
                            "La quantité à déplacer pour le produit %s est supérieure au stock actuel. "
                            "Vous avez seulement %s produits en stock dans l'emplacement %s."
                        ) % (move.product_id.display_name, available_quantity, move.location_id.display_name))
           
      
    def button_validate(self):
        res = super(Stock, self).button_validate()
        for rec in self:
            if rec.picking_type_id.is_picking :
                # Mettre à jour qty_delivered sur les lignes de commande
                for move in rec.move_ids:  # Utiliser move_ids au lieu de move_lines
                    if move.sale_line_id:  # Vérifier si le mouvement est lié à une ligne de commande
                        total_received = move.quantity_done  # Quantité reçue pour ce mouvement
                        sale_line = move.sale_line_id
                        sale_line.qty_delivered += total_received  # Ajouter au champ qty_delivered
                rec.sale_id.action_create_draft_invoice()
            # Si l'opération est de livraison
            if rec.picking_type_id.is_delivery:
                if rec.sale_id:  # Vérifier si une commande est liée à ce transfert
                    draft_invoices = rec.sale_id.customer_invoice_ids.filtered(lambda inv: inv.state == 'draft')
                    if not draft_invoices:
                        raise UserError("Aucune facture brouillon n'est associée à cette commande.")
                    # Comptabiliser toutes les factures brouillon
                    for invoice in draft_invoices:
                        invoice.action_post()

            if rec.delivery_id :
                rec.delivery_id.write({'date': time.strftime('%Y-%m-%d')}) 
                
           
            """fonction permettant de recuperer les responsables et les vehicules sur les prochaines etapes"""
            
            # if rec.picking_step_stk == 'step2':
            #     next_picking = self.env['stock.picking'].search([
            #         ('sale_id', '=', rec.sale_id.id),
            #         ('state', '=', 'waiting'),
            #         # ('scheduled_date', '=', rec.sale_id.scheduled_date)
            #     ], limit=1, order='scheduled_date asc')
                           
            #     if next_picking:
            #         # Ajouter d'autres champs si nécessaire
            #         next_picking.user_id = rec.user_id        
            #         next_picking.fleet_vehicle_id = rec.fleet_vehicle_id        
                
               
            
            rec.state_assignement = "assigned"
            rec.user_id = rec.batch_id.user_id.id
        
        return res
    
    def action_cancel(self):
        """Annule un picking et met les factures brouillon associées uniquement pour les pickings de type is_picking à annuler"""
        for picking in self:
            # Vérifier si l'opération est de type picking
            if picking.picking_type_id.is_delivery:
                # Vérifier si une commande de vente est liée
                if picking.sale_id:
                    draft_invoices = picking.sale_id.customer_invoice_ids.filtered(lambda inv: inv.state == 'draft')
                    if draft_invoices:
                        # Annuler les factures en brouillon associées
                        for invoice in draft_invoices:
                            invoice.button_cancel()
        # Appeler la méthode standard pour annuler
        return super(Stock, self).action_cancel()
    
    # def _create_return_picking(self):
    #     vals_list = []
    #     for rec in self.move_ids_without_package:
    #         if rec.gaps > 0 :
    #             location = self.env['stock.location'].search([('complete_name', '=', 'WH/Stock')])
    #             location_dest = self.env['stock.location'].search([('complete_name', '=', 'Partners/Customers')])
    #             # lot_id = self.move_line_ids[:1].lot_name if self.move_line_ids.lot_id else False
    #             # lot_id = rec.product_lot_id  # Récupère tous les lots associés   
    #             return_vals = {
    #                 'scheduled_date': self.scheduled_date,
    #                 'partner_id': self.partner_id.id,
    #                 'picking_type_id': self.picking_type_id.return_picking_type_id.id,
    #                 'location_dest_id': location.id,
    #                 'location_id': location_dest.id,
    #                 'move_ids': [(0, 0, {
    #                     'product_id': rec.product_id.id,
    #                     'name': rec.product_id.name,
    #                     # 'lot_ids': [(6, 0, rec.product_lot_id)] if rec.product_lot_id else [],
    #                     'product_uom_qty': rec.gaps,
    #                     'quantity': rec.gaps,
    #                     # 'product_uom_id': rec.product_uom.id,
    #                     'location_dest_id': location.id,
    #                     'location_id': location_dest.id,
    #                 })],
    #                 'origin': f"Retour de {self.name}",
                    
    #             }
                        
    #             # Créer le lot
    #             lot = self.env['stock.lot'].search([('name', '=', rec.product_lot_id.id)], limit=1)
                
    #             # Associer le lot au niveau des lignes de mouvement de stock (stock.move.line)
    #             move_line = self.env['stock.move.line'].search([('move_id', '=', rec.id)], limit=1)
    #             if move_line:
    #                 move_line.write({
    #                     'lot_id': lot.id,
    #                     'lot_name': lot.name,
    #                     'location_id': rec.location_id.id,
    #                     'location_dest_id': rec.location_dest_id.id,
    #                 })
    #             rec.write({'lot_ids': [(4, lot.id)]})    
                    
    #             vals_list.append(return_vals)  # Ajouter chaque dictionnaire de valeurs de paiement à la liste
                
    #     if vals_list:
    #         returns_picking = self.env['stock.picking'].create(vals_list)
    #         returns_picking.action_confirm()
    #         # returns_picking.button_validate()
           
    #         return returns_picking
    
class Quality(models.Model):
    _name = 'quality.quality'
    _description = 'Qualités Produits'

    name = fields.Char(string='Libellé Qualité',required=True)
    
      
class Delivery(models.Model):
    _name = 'delivery.delivery'
    _description = 'Qualités Produits'

    ref = fields.Char(string='Référence')
    source = fields.Char(string='Source')
    contact_id = fields.Many2one('res.partner', string="Contact")
    area_id = fields.Many2one('area.area', string="Zone")
    delivery_person_id = fields.Many2one('res.partner', string="Livreur")
    picking_id = fields.Many2one('stock.picking')
    date = fields.Datetime(string='Date de livraison')
    
    
class StockBatch(models.Model):
    _inherit = 'stock.picking.batch'

    deliv_person_id = fields.Many2one("delivery.person",string="Livreur",compute="check_deliv_person")  
    fleet_vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehicule', required=True,)
    # state = fields.Selection([
    #     ('draft', 'Brouillon'),
    #     ('in_progress', 'En cours'),
    #     ('delivered', 'Livré'),
    #     ('done', 'Validé'),
        
    #     ('cancel', 'Annulé')], default='draft',
    #     store=True, compute='_compute_state',
    #     copy=False, tracking=True, readonly=True, index=True)
    
    qty_total = fields.Float(string="Quantities total")
    product_quantity_ids = fields.One2many('product.quantity.batch', 'batch_id', string="Produits par Lot", store=True)
   
    def action_grouped_products(self):
        """
        Calcule automatiquement les produits et quantités regroupés.
        """
        for batch in self:
            grouped_data = batch.group_products_and_quantities()
            batch.product_quantity_ids = [
                (0, 0, {
                    'batch_id': batch.id,
                    'product_id': data['product_id'],
                    'lot_name': data['lot_name'],
                    'total_quantity': data['total_quantity'],
                })
                for data in grouped_data
            ]
    

    def group_products_and_quantities(self):
        """
        Regroupe les produits par ID et calcule la somme totale des quantités.
        :return: Liste de tuples [(product_id, product_name, total_quantity), ...]
        """
        grouped_data = defaultdict(lambda: defaultdict(float))

        # Parcours des lignes d'opération
        for picking in self:
            for line in picking.move_line_ids:
                if line.product_id:
                    lot_name = line.lot_id.name if line.lot_id else " "
                    grouped_data[line.product_id][lot_name] += line.quantity

        # Transformation des données en liste
        result = []
        for product, lots in grouped_data.items():
            for lot_name, total_qty in lots.items():
                result.append({
                    'product_id': product.id,
                    'product_name': product.display_name,
                    'lot_name': lot_name,
                    'total_quantity': total_qty,
                })
        return result
        
    
    def action_delivered(self):
        self.state = 'delivered'
    
    @api.depends('picking_ids')
    def check_deliv_person(self):
        for rec in self:
            if rec.picking_ids:
                # Récupère le nom du livreur de la première ligne d'opération
                rec.deliv_person_id = rec.picking_ids[0].agent_id
            else:
                rec.deliv_person_id = " "    
                
    def action_print_preparation(self):
        self.ensure_one()
        return self.env.ref('edilac.report_preparation').report_action(self)
         
    def action_print_bon_preparation(self):
        self.ensure_one()
        return self.env.ref('edilac.report_bon_preparation').report_action(self)

    def action_print_bc(self):
        self.ensure_one()
        return self.env.ref('edilac.report_bon_commande').report_action(self)

    def action_print_bl(self):
        self.ensure_one()
        return self.env.ref('edilac.report_bl').report_action(self)

  
class ProductQuantityBatch(models.TransientModel):  # Utilisation de TransientModel pour éviter de persister
    _name = 'product.quantity.batch'
    _description = 'Produits et Quantités par Lot'

    batch_id = fields.Many2one('stock.picking.batch', string="Lot de transfert",)
    product_id = fields.Many2one('product.product', string="Produit", )
    product_name = fields.Char(string="Nom du produit", related='product_id.display_name', store=True)
    lot_name = fields.Char(string="Lot")
    total_quantity = fields.Float(string="Quantité totale")    
    
class StockLot(models.Model):
    _inherit = 'stock.lot'

    product_qty = fields.Float('En stock', compute='_product_qty', search='_search_product_qty',store=True)
    statut = fields.Selection(string=_('Statut'),
        selection=[
            ('avalaible', 'Disponible'),
            ('delivery', 'Livré'),
        ], compute='_compute_statut', store=True)

    customer_affection_ids = fields.One2many(comodel_name='freezer.assignment', inverse_name='lot_id', string='Affectation Client', required=False)
    customer_affection_count = fields.Integer(string="'Nombre d'Affectation",    required=False, compute="_compute_customer_affection_count", store=True)
    contract_ids = fields.One2many(comodel_name='customer.contract', inverse_name='lot_id',string='Historique Congélateur', readonly=True)
    last_assignment = fields.Char(string='Dernière affectation chez', compute='_compute_last_assignment', store=True)

    @api.depends('product_qty')
    def _compute_statut(self):
        for lot in self:
            if lot.product_qty > 0:
                lot.statut = 'avalaible'
            elif lot.product_qty == 0:
                lot.statut = 'delivery'
                
    @api.depends('customer_affection_ids')
    def _compute_last_assignment(self):
        """Cette fonction permet de connaître la dernière affectation et le nom du client concerné"""
        for lot in self:
            # Si aucune affectation, laisser vide
            if not lot.customer_affection_ids:
                lot.last_assignment = ''
                continue
            # Trier les affectations par date décroissante
            last_assignment = lot.customer_affection_ids.sorted(lambda a: a.date, reverse=True)[:1]
            if last_assignment:
                # Construire une chaîne avec le nom du client et le numéro de série
                lot.last_assignment = f"{last_assignment.customer_id.name} ({last_assignment.lot_id.name})"
            else:
                lot.last_assignment = ''

    def button_open_customer_affection_count(self):
        """Est une fonction permettant de créer le box intelligent et les données"""
        return {

            'name': 'Affectation Client',
            'res_model': 'freezer.assignment',
            'view_mode': 'list,form',
            'context': {'edit': False, 'create': False},
            'domain': [('lot_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

    @api.depends('customer_affection_ids')
    def _compute_customer_affection_count(self):
        """Elle permet de compter le nombre d'affectation dans le box intelligent"""
        for rec in self:
            rec.customer_affection_count = len(rec.customer_affection_ids)


class StockLotType(models.Model):
    _inherit = 'stock.picking.type'

    is_free_transfer = fields.Boolean(string='Deploiement congelateur', default=False)
    type_code = fields.Char(string="Code Type Picking (première ligne)")
    step = fields.Selection(
        string=_('Etape livraison'),
        selection=[
            ('step1', 'Etape 1'),
            ('step2', 'Etape 2'),
            ('step3', 'Etape 3'),
            ('step4', 'Etape 4'),
        ],
    )
    is_picking = fields.Boolean(string='Commande de livraison', default=False)
    is_delivery = fields.Boolean(string='Bon de livraison', default=False) # Permet de détecter le dernier niveau dans le processus de validation des livraisons dans (stock.picking)

class StockMove(models.Model):
    _inherit = 'stock.move.line'

    product_packaging_id = fields.Many2one('product.packaging', 'Conditionnement',related="move_id.product_packaging_id")
    price_unit = fields.Float(string="Prix unitaire", compute="compute_price_unit")
    price_subtotal = fields.Monetary(string="Prix HT", compute="compute_price_unit")
    price_total = fields.Monetary(string="Prix TTC", compute="compute_price_unit")
    currency_id = fields.Many2one('res.currency', 'Devise', default=lambda self: self.env.company.currency_id,
                                  readonly=True, required=True)
    #taxes = fields.Char(string="Taxes", compute="compute_price_unit")
    taxes = fields.Monetary(string="Montant de la Taxe", compute="compute_price_unit")  # Nouveau champ pour le montant de la taxe
    tax_percent = fields.Char(string="Taxe (%)", compute="_compute_tax_percent")

    @api.depends('picking_id.sale_id.order_line.tax_id')
    def _compute_tax_percent(self):
        for rec in self:
            taxes = rec.picking_id.sale_id.order_line.filtered(lambda l: l.product_id == rec.product_id).tax_id
            if taxes:
                # Concatène les pourcentages de toutes les taxes liées
                rec.tax_percent = ', '.join(f"{tax.amount}%" for tax in taxes)
            else:
                rec.tax_percent = "0%"

    @api.depends('picking_id.sale_id.order_line.price_unit')
    def compute_price_unit(self):
        for rec in self:
            for line in rec.picking_id.sale_id.order_line:
                if line.product_id == rec.product_id:
                    rec.price_unit = line.price_unit
                    rec.price_subtotal = line.price_subtotal
                    rec.price_total = line.price_total
                    # Calcul du montant de la taxe
                    tax_amount = 0
                    for tax in line.tax_id:
                        tax_amount += line.price_subtotal * tax.amount / 100
                    rec.taxes = tax_amount



                            