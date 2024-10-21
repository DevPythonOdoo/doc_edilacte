from odoo import models, fields, api

class Stock(models.Model):
    _inherit = 'stock.move'

    gaps = fields.Float(string="ecart", compute='_compute_ecart',default=0.0, store=True)    

    @api.depends('quantity', 'product_uom_qty')
    def _compute_ecart(self):
        for rec in self:
            if rec.quantity and rec.product_uom_qty:
                rec.gaps = rec.product_uom_qty - rec.quantity

            

class Stock(models.Model):
    _inherit = 'stock.picking'

    total_ordered = fields.Float(string="Total commandé", compute='_cumul_total_sum', store=True, readonly=True)
    total_received = fields.Float(string="Total reçu", compute='_cumul_total_sum', store=True, readonly=True)
    total_ecart = fields.Float(string="Total ecart", compute='_cumul_total_sum', store=True)    
    
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

    