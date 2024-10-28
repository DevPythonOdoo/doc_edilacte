from odoo import models, fields, api,_
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = 'stock.move'

    gaps = fields.Float(string="ecart", compute='_compute_ecart',default=0.00, store=True)  
    quality_id = fields.Many2one(comodel_name='quality.quality',string='Qualité')  

    @api.depends('quantity', 'product_uom_qty')
    def _compute_ecart(self):
        for rec in self:
            if rec.quantity and rec.product_uom_qty:
                rec.gaps = rec.product_uom_qty - rec.quantity
 

class Stock(models.Model):
    _inherit = 'stock.picking'

    total_ordered = fields.Float(string="Total commandé",default=0.00, compute='_cumul_total_sum', store=True, readonly=True)
    total_received = fields.Float(string="Total reçu", default=0.00, compute='_cumul_total_sum', store=True, readonly=True)
    total_ecart = fields.Float(string="Total ecart",default=0.00, compute='_cumul_total_sum', store=True, readonly=True)    
    
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


    def _check_stock_availability(self):
        """ Vérification de la disponibilité du stock pour chaque mouvement avant la confirmation du picking. """
        for picking in self:
            if picking.picking_type_code == 'internal':
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
        # Appeler la vérification de stock avant de valider le picking
        self._check_stock_availability()
        
        # Appeler la méthode parent pour valider l'opération
        return super(Stock, self).button_validate()

class Quality(models.Model):
    _name = 'quality.quality'
    _description = 'Qualités Produits'

    name = fields.Char(string='Libellé Qualité',required=True)
      
 