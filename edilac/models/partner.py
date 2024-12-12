from odoo.tools import float_is_zero

from odoo.exceptions import UserError

from odoo import models, fields, api, _, exceptions
from datetime import datetime


class Partner(models.Model):
    _inherit = 'res.partner'


    # customer_type = fields.Selection(string='Type de client', selection=[('tva', 'TVA OU TOTAL'), ('normal', 'Normal'),
    #                                                                      ('normal_d', 'Normal déclaré')])
    customer_profil = fields.Selection(string='Profil client', selection=[('on', 'ON-US'), ('off', 'OFF-US')])

    customer_type_id = fields.Many2one(comodel_name='customer.type', string='Type de client')
    region_id = fields.Many2one(comodel_name='region.region', string='Region')
    city_id = fields.Many2one(comodel_name='city.city', string='Ville')
    area_id = fields.Many2one(comodel_name='area.area', string='Zone')
    common_id = fields.Many2one(comodel_name='common.common', string='Commune')
    num_registre = fields.Char(string='N° Registre du commerce')
    neighborhood_id = fields.Many2one(comodel_name='neighborhood.neighborhood', string='Quartier')
    supplier_type = fields.Selection(string='Catégorie Fournisseur',
                                     selection=[('national', 'National'), ('international', 'International')])
    delivery_person = fields.Boolean(string='Livreur', default=False)
    # freezer_ids = fields.One2many('partner.freezer', 'partner_id', string="Congélateurs")
    forecast_ids = fields.One2many('business.forecast', 'partner_id', string="Prévisions Commerciales",readonly=True)

    assignment_ids = fields.One2many(comodel_name='customer.contract', readonly=True, inverse_name='customer_id',string='Contrat client', required=False)
    nbre = fields.Integer(string='Nbre Congelateur', compute="_compute_freezer", required=False)
    capacity = fields.Integer(string='Capacité Congelateur', compute="_compute_freezer", required=False)
    contact_select = fields.Boolean(string='Contact sélectionné', default=False)
    

    def _compute_freezer2(self):
        for rec in self:
            rec.assignment_ids = len(rec.assignment_ids.filtered(lambda x: x.state == 'in_progress'))

    def _compute_freezer(self):
        for rec in self:
            rec.nbre = len(rec.assignment_ids.filtered(lambda x: x.state == 'in_progress'))
            rec.capacity = sum(line.freezer_capacity for line in rec.assignment_ids.filtered(lambda x: x.state == 'in_progress'))

    @api.depends('parent_id')
    def _compute_team_id(self):
        for partner in self.filtered(lambda p: not p.team_id and p.company_type == 'person' and p.parent_id.team_id):
            # Vérifiez si l'équipe parent a au moins un commercial actif
            if partner.parent_id.team_id.has_salesperson:
                partner.team_id = partner.parent_id.team_id
                
   
                    
class CustomerType(models.Model):
    _name = 'customer.type'
    _description = 'Type de client'

    name = fields.Char(string='Nom', required=True)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,
                                 default=lambda self: self.env.company.id)




"""
+++++++++++++++++++++ 
CLASS OBJECTS
+++++++++++++++++++++
"""





class Region(models.Model):
    _name = 'region.region'
    _description = 'Region'

    name = fields.Char(string='Région', required=True)
    city_ids = fields.One2many(comodel_name='city.city', inverse_name='region_id', string="Ville")
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,
                                 default=lambda self: self.env.company.id)


class City(models.Model):
    _name = 'city.city'
    _description = 'Ville'

    name = fields.Char(string='Ville', required=True)
    region_id = fields.Many2one(comodel_name='region.region', required=True, string='Region')
    area_ids = fields.One2many(comodel_name='area.area', inverse_name='city_id', string="Zone")
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,
                                 default=lambda self: self.env.company.id)


class Area(models.Model):
    _name = 'area.area'
    _description = 'Zone'

    name = fields.Char(string='Zone', required=True)
    city_id = fields.Many2one(comodel_name='city.city', string='Ville', required=True)
    common_ids = fields.One2many(comodel_name='common.common', inverse_name='area_id', string="Commune")
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,
                                 default=lambda self: self.env.company.id)
    contact_select = fields.Boolean(string='Contact sélectionné', default=False)


class Common(models.Model):
    _name = 'common.common'
    _description = 'Commune'

    name = fields.Char(string='Commune', required=True)
    area_id = fields.Many2one(comodel_name='area.area', string='Zone', required=True, )
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,
                                 default=lambda self: self.env.company.id)
    neighborhood_ids = fields.One2many(comodel_name='neighborhood.neighborhood', inverse_name='common_id',
                                       string="Quartier")
    contact_select = fields.Boolean(string='Contact sélectionné', default=False)


class Neighborhood(models.Model):
    _name = 'neighborhood.neighborhood'
    _description = 'Quartier'
    name = fields.Char(string='Quartier', required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True, default=lambda self: self.env.company.id)
    common_id = fields.Many2one(comodel_name='common.common', string='Commune', required=True, )
    contact_select = fields.Boolean(string='Contact sélectionné', default=False)
