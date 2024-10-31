from odoo.tools import float_is_zero

from odoo.exceptions import UserError

from odoo import models, fields, api,_,exceptions
from datetime import datetime



class Partner(models.Model):
    _inherit = 'res.partner'


    # date_create_customer =fields.Datetime(string='Date Création client', default=fields.Datetime.now)
    family_cust = fields.Many2one(comodel_name='family.custom',string='Famille client')
    customer_type = fields.Selection(string='Type de client',selection=[('tva', 'TVA OU TOTAL'),('normal', 'Normal'), ('normal_d', 'Normal déclaré') ])
    customer_profil = fields.Selection(string='Profil client',selection=[('on', 'ON-US'),('off', 'OFF-US')])
    #payment_mode = fields.Selection(string='Mode de paiement', selection=[('espece', 'Espèce'), ('check', 'Chèque/Virement'), ])
    # airsi = fields.Char(string='AIRSI')
    region_id = fields.Many2one(comodel_name='region.region', string='Region')
    city_id = fields.Many2one(comodel_name='city.city',string='Ville')
    area_id = fields.Many2one(comodel_name='area.area',string='Zone')
    common_id = fields.Many2one(comodel_name='common.common',string='Commune')
    num_registre = fields.Char(string='N° Registre du commerce')
    neighborhood_id = fields.Many2one(comodel_name='neighborhood.neighborhood',string='Quartier')
    supplier_type = fields.Selection(string='Catégorie Fournisseur',selection=[('national', 'National'), ('international', 'International')])
    delivery_person = fields.Boolean(string='Livreur', default=True)
    freezer_ids = fields.One2many('partner.freezer', 'partner_id', string="Congélateurs")
    nbre = fields.Integer(string='Nbre Congelateur', compute="_compute_freezer",required=False)

    def _compute_freezer(self):
        for rec in self:
            rec.nbre = len(rec.freezer_ids)

    @api.depends('parent_id')
    def _compute_team_id(self):
        for partner in self.filtered(lambda p: not p.team_id and p.company_type == 'person' and p.parent_id.team_id):
            # Vérifiez si l'équipe parent a au moins un commercial actif
            if partner.parent_id.team_id.has_salesperson:
                partner.team_id = partner.parent_id.team_id    
class producpricelist(models.Model):
    _inherit = 'product.pricelist'

    state = fields.Selection(
        string=_('state'),
        selection=[
            ('draft', 'Nouveau'),
            ('send', 'Soumis'),
            ('done', 'Validé'),
        ], default='draft',readonly=True, tracking=True,
    )

    def action_submit(self):
        for rec in self:
            if not rec.item_ids :
                raise exceptions.UserError('Veuillez ajouter des règles de tarification pour cette liste de prix.')
        self.write({"state": "send"})
    
    def action_validate(self):
        self.write({"state": "done"})
    
    def action_cancel(self):
        self.write({"state": "draft"})
        
"""
+++++++++++++++++++++ 
CLASS OBJECTS
+++++++++++++++++++++
""" 

class Family(models.Model):
    _name = 'family.custom'
    _description = 'Famille de client'

    name = fields.Char(string='Famille client')
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,default=lambda self: self.env.company.id)

class Region(models.Model):
    _name = 'region.region'
    _description = 'Region'

    name = fields.Char(string='Région',required=True)
    city_ids = fields.One2many(comodel_name='city.city', inverse_name='region_id',string="Ville") 
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,default=lambda self: self.env.company.id)
 
    
class City(models.Model):
    _name = 'city.city'
    _description = 'Ville'

    name = fields.Char(string='Ville',required=True)
    region_id = fields.Many2one(comodel_name='region.region',required=True,string='Region')
    area_ids = fields.One2many(comodel_name='area.area', inverse_name='city_id',string="Zone")
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,default=lambda self: self.env.company.id)
 

class Area(models.Model):
    _name = 'area.area'
    _description = 'Zone'

    name = fields.Char(string='Zone',required=True)
    city_id = fields.Many2one(comodel_name='city.city',string='Ville',required=True)
    common_ids = fields.One2many(comodel_name='common.common', inverse_name='area_id',string="Commune")
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,default=lambda self: self.env.company.id)
 

class Common(models.Model):
    _name = 'common.common'
    _description = 'Commune'

    name = fields.Char(string='Commune',required=True)
    area_id = fields.Many2one(comodel_name='area.area',string='Zone',required=True,)
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,default=lambda self: self.env.company.id)
    neighborhood_ids = fields.One2many(comodel_name='neighborhood.neighborhood', inverse_name='common_id',string="Quartier") 


class Neighborhood(models.Model):
    _name = 'neighborhood.neighborhood'
    _description = 'Quartier'
    name = fields.Char(string='Quartier',required=True)
    company_id = fields.Char(string='Company',required=True)
    common_id = fields.Many2one(comodel_name='common.common',string='Commune',required=True,)


class PartnerFreezer(models.Model):
    _name = 'partner.freezer'
    _description = 'Congélateur lié au client'

    product_id = fields.Many2one('product.product',string="Nom du Congélateur",domain=[('freezer', '=', True)],help="Sélectionner un produit marqué comme congélateur")
    capacity = fields.Float(related='product_id.capacity',string="Capacité", help="Capacité du congélateur en litres")
    partner_id = fields.Many2one('res.partner', string="Client", ondelete='cascade')
    freezer_number = fields.Integer(string="Nombre de Congélateur", default=1)
    turnover = fields.Float(string="Chiffre d'affaire")

#     @api.model
#     def create(self, vals):
#         product = self.env['product.product'].browse(vals['product_id'])
#         freezer_qty = vals.get('freezer_number', 1)  # Utilise freezer_number pour la quantité
#
#         # Vérifie si la quantité disponible est suffisante
#         if product.qty_available < freezer_qty:
#             raise UserError(f"Stock insuffisant pour le produit {product.name}. Stock actuel : {product.qty_available}")
#
#         # Emplacements source et destination explicites
#         location_id = self.env['stock.location'].search([('complete_name', '=', 'WH/Stock')], limit=1)
#         location_dest_id = self.env['stock.location'].search([('complete_name', '=', 'Partners/Vendors')], limit=1)
#         if not location_id:
#             raise UserError("L'emplacement 'WH/STOCK' n'a pas été trouvé.")
#
#         picking_type_out = self.env.ref('stock.picking_type_out')  # Type de picking de sortie
#         picking = self.env['stock.picking'].create({
#             'partner_id': vals['partner_id'],
#             'picking_type_id': picking_type_out.id,
#             'location_id': location_id.id,
#             'location_dest_id': location_dest_id.id,
#         })
#
#         # Crée un mouvement de stock en état brouillon (sortie)
#         stock_move = self.env['stock.move'].create({
#             'name': f'Affectation de {freezer_qty} congélateur(s) {product.name} au client {vals["partner_id"]}',
#             'product_id': product.id,
#             'product_uom_qty': freezer_qty,
#             'product_uom': product.uom_id.id,
#             'location_id': location_id.id,  # Emplacement source (stock)
#             'location_dest_id': location_dest_id.id,
#             'state': 'draft',
#             'picking_id': picking.id, # Démarre en état brouillon
#         })
#
#         # Confirme et effectue le mouvement
#
#         picking.button_validate_test()
#
#         # Crée le congélateur pour le client après le mouvement de stock
#         record = super().create(vals)
#
#         return record
#
# class Stock(models.Model):
#     _inherit = 'stock.picking'
#
#     def button_validate_test(self):
#         draft_picking = self.filtered(lambda p: p.state == 'draft')
#         draft_picking.action_confirm()
#         for move in draft_picking.move_ids:
#             if float_is_zero(move.quantity, precision_rounding=move.product_uom.rounding) and\
#                not float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
#                 move.quantity = move.product_uom_qty
#
#         # Sanity checks.
#         if not self.env.context.get('skip_sanity_check', False):
#             self._sanity_check()
#         self.message_subscribe([self.env.user.partner_id.id])
#
#         # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
#         # moves and/or the context and never call `_action_done`.
#         if not self.env.context.get('button_validate_picking_ids'):
#             self = self.with_context(button_validate_picking_ids=self.ids)
#         res = self._pre_action_done_hook()
#         if res is not True:
#             return res
#
#         # Call `_action_done`.
#         pickings_not_to_backorder = self.filtered(lambda p: p.picking_type_id.create_backorder == 'never')
#         if self.env.context.get('picking_ids_not_to_backorder'):
#             pickings_not_to_backorder |= self.browse(self.env.context['picking_ids_not_to_backorder']).filtered(
#                 lambda p: p.picking_type_id.create_backorder != 'always'
#             )
#         pickings_to_backorder = self - pickings_not_to_backorder
#         pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
#         pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
#         report_actions = self._get_autoprint_report_actions()
#         another_action = False
#         if self.user_has_groups('stock.group_reception_report'):
#             pickings_show_report = self.filtered(lambda p: p.picking_type_id.auto_show_reception_report)
#             lines = pickings_show_report.move_ids.filtered(lambda m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity and not m.move_dest_ids)
#             if lines:
#                 # don't show reception report if all already assigned/nothing to assign
#                 wh_location_ids = self.env['stock.location']._search([('id', 'child_of', pickings_show_report.picking_type_id.warehouse_id.view_location_id.ids), ('usage', '!=', 'supplier')])
#                 if self.env['stock.move'].search([
#                         ('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
#                         ('product_qty', '>', 0),
#                         ('location_id', 'in', wh_location_ids),
#                         ('move_orig_ids', '=', False),
#                         ('picking_id', 'not in', pickings_show_report.ids),
#                         ('product_id', 'in', lines.product_id.ids)], limit=1):
#                     action = pickings_show_report.action_view_reception_report()
#                     action['context'] = {'default_picking_ids': pickings_show_report.ids}
#                     if not report_actions:
#                         return action
#                     another_action = action
#         if report_actions:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'do_multi_print',
#                 'params': {
#                     'reports': report_actions,
#                     'anotherAction': another_action,
#                 }
#             }
#         return True
