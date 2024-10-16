from odoo import models, fields, api
from datetime import datetime


class Partner(models.Model):
    _inherit = 'res.partner'


    date_create_customer =fields.Datetime(string='Date Création client', default=fields.Datetime.now)
    family_cust = fields.Many2one(comodel_name='family.custom',string='Famille client')
    customer_type = fields.Selection(string='Type de client',selection=[('tva', 'TVA OU TOTAL'),('normal', 'Normal'), ])
    custom_profil = fields.Char(string='Profil client')
    #payment_mode = fields.Selection(string='Mode de paiement', selection=[('espece', 'Espèce'), ('check', 'Chèque/Virement'), ])
    airsi = fields.Char(string='AIRSI')
    region_id = fields.Many2one(comodel_name='region.region', string='Region')
    city_id = fields.Many2one(comodel_name='city.city',string='Ville')
    area_id = fields.Many2one(comodel_name='area.area',string='Zone')
    common_id = fields.Many2one(comodel_name='common.common',string='Commune')
    num_registre = fields.Integer(string='N° Registre du commerce')
    day_visit = fields.Integer(string='Jour visite')

    supplier_type = fields.Selection(string='Catégorie Fournisseur',
                                     selection=[('national', 'National'), ('international', 'International'), ])


    @api.onchange('region_id')
    def _onchange_region_id(self):
    
    #Filtrer les villes en fonction de la région sélectionnée
        
        for record in self:
            if record.region_id:
                # Filtrer les villes dont la région correspond à la région sélectionnée
                #record.city_id = record.region_id.mapped('city_ids').id
                return {'domain': {'city_id': [('region_id', '=', record.region_id.id)]}}
            

    @api.onchange('city_id')
    def _onchange_field4_id(self):
        for record in self:
            if record.region_id:
                
                return {'domain': {'area_id': [('city_id', '=', record.city_id.id)]}}
                      
                    
    

class Family(models.Model):
    _name = 'family.custom'
    _description = 'Famille de client'

    name = fields.Char(string='Famille client')

class Region(models.Model):
    _name = 'region.region'
    _description = 'Region'

    name = fields.Char(string='Famille client')
    city_ids = fields.One2many(comodel_name='city.city', inverse_name='region_id',string="Ville", required=True)  
    area_ids = fields.One2many(comodel_name='area.area', inverse_name='region_id',string='Zone')
    common_ids = fields.One2many(comodel_name='common.common', inverse_name='region_id',string='Commune') 

class City(models.Model):
    _name = 'city.city'
    _description = 'Ville'

    name = fields.Char(string='Ville',required=True)
    region_id = fields.Many2one(comodel_name='region.region',string='Region')
    area_ids = fields.One2many(comodel_name='area.area', inverse_name='city_id',string="Zone", required=True) 

class Area(models.Model):
    _name = 'area.area'
    _description = 'Zone'

    name = fields.Char(string='Zone',required=True)
    region_id = fields.Many2one(comodel_name='region.region',string='Region')
    city_id = fields.Many2one(comodel_name='city.city',string='Ville')
    common_ids = fields.One2many(comodel_name='common.common', inverse_name='area_id',string="Commune", required=True) 

    

class Common(models.Model):
    _name = 'common.common'
    _description = 'Commune'

    name = fields.Char(string='Commune',required=True)
    region_id = fields.Many2one(comodel_name='region.region',string='Region')
    area_id = fields.Many2one(comodel_name='area.area',string='Zone')
