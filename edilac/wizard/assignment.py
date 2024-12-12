import babel
from datetime import datetime, time
from odoo import fields, models, api,exceptions,tools
from odoo.exceptions import UserError
import logging as _logger


class Assignment(models.Model):
    _name = 'assignment.assignment'

    #name = fields.Char(string='Name', required=False,default="Paiement Partiel",)
    order_selected_ids = fields.One2many(comodel_name='assignment.line.wz', inverse_name="wz_id", string='Affectation', required=False)
    area_select_ids = fields.One2many(comodel_name='area.wz', string='Zone',inverse_name="wz_id", required=False)
    common_selected_ids = fields.One2many(comodel_name='common.wz', inverse_name="wz_id", string='Affectation', required=False)
    neighborhood_selected_ids = fields.One2many(comodel_name='neighborhood.wz', inverse_name="wz_id", string='Affectation', required=False)
    delivery_agent_id = fields.Many2one('delivery.person', 'Livreur', required=True, store=True)
    batch_id = fields.Many2one('stock.picking.batch', string="Lot de transfert", required=False)
   
    contacts_ids = fields.Many2many('res.partner', string='Clients')
    area_ids = fields.Many2many('area.area', string='Zone')
    common_ids = fields.Many2many('common.common', string='Commune')
    neighborhood_ids = fields.Many2many('neighborhood.neighborhood', string='Quartier')
    criteria = fields.Selection([
        ('customer', 'Client'),
        ('area', 'Zone'),
        ('common', 'Commune'),
        ('neighborhood', 'Quartier'),], default='customer',string='Critère')
    related_delivery_ids = fields.One2many(
        'stock.picking', inverse_name="assignment_id",
        string="Commandes liées", 
        store=True
    )
    related_area_ids = fields.Many2many(
        'area.wz2', 
        string="Commandes liées", 
        #compute="_compute_related_delivery_ids",
        store=False
    )
    related_common_ids = fields.Many2many(
        'common.wz2', 
        string="Commandes liées", 
        #compute="_compute_related_delivery_ids",
        store=False
    )
    related_neigh_ids = fields.Many2many(
        'neighborhood.wz2', 
        string="Commandes liées", 
        #compute="_compute_related_delivery_ids",
        store=False
    )
    company_id = fields.Many2one(comodel_name='res.company', string='Société',
                                 default=lambda self: self.env.company.id)
    fleet_vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehicule', required=True,)

    

    @api.onchange('contacts_ids','common_ids','area_ids','neighborhood_ids', 'order_selected_ids','area_select_ids','common_selected_ids','neighborhood_selected_ids')
    def _compute_related_delivery_ids(self):
        for rec in self:
            # Initialiser les commandes liées
            deliveries = self.env['stock.picking']
            deliveries_a = self.env['stock.picking']
            deliveries_c = self.env['stock.picking']
            deliveries_n = self.env['stock.picking']

            # Filtrer les lignes de `order_selected_ids` pour récupérer les commandes associées aux contacts sélectionnés
            if rec.contacts_ids:
                selected_contacts = rec.contacts_ids.ids
                deliveries = rec.order_selected_ids.filtered(
                    lambda line: line.contact_id.id in selected_contacts
                ).mapped('delivery_id')
                rec.related_delivery_ids = deliveries
            if rec.area_ids:
                selected_contacts = rec.area_ids.ids
                deliveries_a = rec.order_selected_ids.filtered(
                    lambda line: line.area_id.id in selected_contacts
                ).mapped('delivery_id')
                rec.related_delivery_ids = deliveries_a
            if rec.common_ids:
                selected_contacts = rec.common_ids.ids
                deliveries_c = rec.order_selected_ids.filtered(
                    lambda line: line.common_id.id in selected_contacts
                ).mapped('delivery_id')
                rec.related_delivery_ids = deliveries_c
            if rec.neighborhood_ids:
                selected_contacts = rec.neighborhood_ids.ids
                deliveries_n = rec.order_selected_ids.filtered(
                    lambda line: line.neighborhood_id.id in selected_contacts
                ).mapped('delivery_id')
                rec.related_delivery_ids = deliveries_n
          
    
    @api.model
    def default_get(self, fields):
        
        res = super(Assignment, self).default_get(fields)
        active_id = self.env.context.get('active_ids', [])
        vals = []
        area_ids = []
        common_ids = []
        quartier_ids = []
        for rec in self.env['stock.picking'].browse(active_id):
            if rec.state in ('assigned'):
                line_id = (0, 0, {
                    "wz_id": self.id,
                    "delivery_id": rec.id,
                    "contact_select_wz": True,
                })
                line2_id = (0, 0, {
                    "wz_id": self.id,
                    "delivery_id": rec.id,
                    "area_id": rec.area_id,
                    "contact_select_wz": True,
                })
                line3_id = (0, 0, {
                    "wz_id": self.id,
                    "delivery_id": rec.id,
                    "common_id": rec.common_id,
                    "contact_select_wz": True,
                })
                line4_id = (0, 0, {
                    "wz_id": self.id,
                    "delivery_id": rec.id,
                    "neighborhood_id": rec.neighborhood_id,
                    "contact_select_wz": True,
                })
                vals.append(line_id)
                area_ids.append(line2_id)
                common_ids.append(line3_id)
                quartier_ids.append(line4_id)
                
                # Mettre à jour `contact_select` pour le contact lié (si existe)
                if rec.partner_id :
                    rec.partner_id.contact_select = True
                if rec.area_id :
                    rec.area_id.contact_select = True
                if rec.common_id :
                    rec.common_id.contact_select = True
                if rec.neighborhood_id :
                    rec.neighborhood_id.contact_select = True
                 
                

        # Mettre à jour la réponse avec les champs Many2many pour la vue
        res.update({
            'order_selected_ids': vals,
            'area_select_ids': area_ids,
            'common_selected_ids': common_ids,  
            'neighborhood_selected_ids': quartier_ids,  
        })

        return res

   
    """
    def default_get(self, fields):
       
        res = super(Assignment, self).default_get(fields)
        active_id = self.env.context.get('active_ids', [])
        vals = []
        contact_ids = []
        area_ids = []
        for rec in self.env['stock.picking'].browse(active_id):
            if rec.state in ('assigned'):
                line_id = (0, 0, {
                    "wz_id": self.id,
                    "delivery_id": rec.id,
                })
                vals.append(line_id)
                if rec.area_id:
                    area_ids.append(rec.area_id.id)
                
                # Récupération des contacts depuis les enregistrements stock.picking
                if rec.partner_id:
                    contact_ids.append(rec.partner_id.id)
        res.update({
            #'name': "Affectation",
            'order_selected_ids': vals,
            'area_select_ids': [(6, 0, list(set(area_ids)))],
            #'common_selected_ids': vals,
            #'neighborhood_selected_ids': vals,
            'contacts_ids': [(6, 0, list(set(contact_ids)))],  # Utilisation d'un set pour éliminer les doublons
        })
        return res
    """
    # @api.onchange('delivery_person_id')
    # def _onchange_appli_person(self):
    #      for record in self.related_delivery_ids:
    #         if self.delivery_person_id:
    #             record.deliv_person_id = self.delivery_person_id
           
                

    def action_assignments(self):
        # Vérifier si une ou plusieurs commandes ont déjà le statut "affecté"
        already_assigned = self.related_delivery_ids.filtered(lambda rec: rec.state_assignement == "assigned")
        if already_assigned:
            assigned_names = ', '.join(already_assigned.mapped('name'))
            raise UserError(f"Les commandes suivantes sont déjà affectées : {assigned_names}")

         # Créer un nouveau transfert par lot
        picking_batch = self.env['stock.picking.batch'].create({
            'scheduled_date': fields.Datetime.now(),
            #'user_id': self.user_id.id,
            'fleet_vehicle_id': self.fleet_vehicle_id.id,
            'company_id': self.company_id.id,
            'picking_ids': [(4, picking.id) for picking in self.related_delivery_ids],
        })
        for rec in self.related_delivery_ids:
            ttyme = datetime.combine(fields.Date.from_string(rec.date), time.min)
            ref = rec.name
            delivery_person = rec.agent_id
            source = rec.origin
            contact_id = rec.partner_id
            area_id = rec.area_id
            
            rec.delivery_id.write({'batch_id': picking_batch.id})
            rec.state_assignement = "assigned"
           
           
        # Mettre à jour le statut du lot de transfert en "En cours"
        picking_batch.user_id = self.delivery_agent_id.user_id.id if self.delivery_agent_id else None
        picking_batch.action_confirm()    
        picking_batch.action_grouped_products()   
        
        return {'type': 'ir.actions.act_window_close'}
        

class PaymentPartial(models.Model):
    _name = 'assignment.line.wz'
    _description = "Ligne de Wizard"

    wz_id = fields.Many2one('assignment.assignment', string="Affectation", required=False, ondelete="cascade")
    delivery_id = fields.Many2one('stock.picking', string="Commande")
    ref = fields.Char(string='Référence', related="delivery_id.name")
    source = fields.Char(string='Source', related="delivery_id.origin")
    date = fields.Datetime(string='Date de livraison', related="delivery_id.scheduled_date")
    contact_id = fields.Many2one('res.partner', string="Contact", related="delivery_id.partner_id")
    area_id = fields.Many2one('area.area', string="Zone", related="delivery_id.area_id")
    common_id = fields.Many2one('common.common', string="Commune", related="delivery_id.common_id")
    neighborhood_id = fields.Many2one('neighborhood.neighborhood', string="Quartier", related="delivery_id.neighborhood_id")
    person_id = fields.Many2one('res.partner', string="Livreur")
    contact_select_wz = fields.Boolean(string='Contact sélectionné', default=False)
    
   
   
    
class AreaWz(models.Model):
    _name = 'area.wz'
    _description = "Ligne de Wizard Zone"

    wz_id = fields.Many2one('assignment.assignment', string="Affectation", required=False, ondelete="cascade")
    delivery_id = fields.Many2one('stock.picking', string="Commande")
    area_id = fields.Many2one('area.area', string="Zone", related="delivery_id.area_id")
    person_id = fields.Many2one('res.partner', string="Livreur")
    ref = fields.Char(string='Référence', related="delivery_id.name")
    source = fields.Char(string='Source', related="delivery_id.origin")
    date = fields.Datetime(string='Date de livraison', related="delivery_id.scheduled_date")
    contact_select_wz = fields.Boolean(string='Contact sélectionné', default=False)

class AreaWz2(models.Model):
    _name = 'area.wz2'
    _description = "Ligne de Wizard Zone2"

    wz_id = fields.Many2one('assignment.assignment', string="Affectation", required=False, store=True, ondelete="cascade")
    delivery_id = fields.Many2one('area.wz',store=True, string="Commande")
    area_id = fields.Many2one('area.area',store=True, string="Zone", related="delivery_id.area_id")
    person_id = fields.Many2one('res.partner',store=True, string="Livreur")
    ref = fields.Char(string='Référence',store=True, related="delivery_id.ref")
    source = fields.Char(string='Source',store=True, related="delivery_id.source")
    date = fields.Datetime(string='Date de livraison',store=True, related="delivery_id.date")
    contact_select_wz = fields.Boolean(string='Contact sélectionné' ,store=True,related="delivery_id.contact_select_wz")

        

class CommonWz(models.Model):
    _name = 'common.wz'
    _description = "Ligne de Wizard Commune"

    wz_id = fields.Many2one('assignment.assignment', string="Affectation", required=False, ondelete="cascade")
    delivery_id = fields.Many2one('stock.picking', string="Commande")
    common_id = fields.Many2one('common.common', string="Commune", related="delivery_id.common_id")
    person_id = fields.Many2one('res.partner', string="Livreur")
    ref = fields.Char(string='Référence', related="delivery_id.name")
    source = fields.Char(string='Source', related="delivery_id.origin")
    date = fields.Datetime(string='Date de livraison', related="delivery_id.scheduled_date")
    contact_select_wz = fields.Boolean(string='Contact sélectionné', default=False)

class CommonWz(models.Model):
    _name = 'common.wz2'
    _description = "Ligne de Wizard Commune2"

    wz_id = fields.Many2one('assignment.assignment', string="Affectation",store=True, required=False, ondelete="cascade")
    delivery_id = fields.Many2one('common.wz', string="Commande",store=True,)
    common_id = fields.Many2one('common.common', string="Commune",store=True, related="delivery_id.common_id")
    person_id = fields.Many2one('res.partner', string="Livreur",store=True,)
    ref = fields.Char(string='Référence',store=True, related="delivery_id.ref")
    source = fields.Char(string='Source',store=True, related="delivery_id.source")
    date = fields.Datetime(string='Date de livraison',store=True, related="delivery_id.date")
    contact_select_wz = fields.Boolean(string='Contact sélectionné' ,store=True,related="delivery_id.contact_select_wz")


class NeighborhoodWz(models.Model):
    _name = 'neighborhood.wz'
    _description = "Ligne de Wizard Quartier"

    wz_id = fields.Many2one('assignment.assignment', string="Affectation", required=False, ondelete="cascade")
    delivery_id = fields.Many2one('stock.picking', string="Commande")
    neighborhood_id = fields.Many2one('neighborhood.neighborhood', string="Zone", related="delivery_id.neighborhood_id")
    person_id = fields.Many2one('res.partner', string="Livreur")
    ref = fields.Char(string='Référence', related="delivery_id.name")
    source = fields.Char(string='Source', related="delivery_id.origin")
    date = fields.Datetime(string='Date de livraison', related="delivery_id.scheduled_date")
    contact_select_wz = fields.Boolean(string='Contact sélectionné', default=False)
    
 
class NeighborhoodWz(models.Model):
    _name = 'neighborhood.wz2'
    _description = "Ligne de Wizard Quartier2"

    wz_id = fields.Many2one('assignment.assignment', string="Affectation",store=True, required=False, ondelete="cascade")
    delivery_id = fields.Many2one('neighborhood.wz', string="Commande",store=True,)
    neighborhood_id = fields.Many2one('neighborhood.neighborhood', string="Zone",store=True, related="delivery_id.neighborhood_id")
    person_id = fields.Many2one('res.partner', string="Livreur",store=True,)
    ref = fields.Char(string='Référence', related="delivery_id.ref",store=True,)
    source = fields.Char(string='Source', related="delivery_id.source",store=True,)
    date = fields.Datetime(string='Date de livraison', related="delivery_id.date",store=True,)
    contact_select_wz = fields.Boolean(string='Contact sélectionné' ,store=True,related="delivery_id.contact_select_wz")

        