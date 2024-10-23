from odoo import models, fields, api
from datetime import datetime


class Partner(models.Model):
    _inherit = 'res.partner'


    # date_create_customer =fields.Datetime(string='Date Création client', default=fields.Datetime.now)
    family_cust = fields.Many2one(comodel_name='family.custom',string='Famille client')
    customer_type = fields.Selection(string='Type de client',selection=[('tva', 'TVA OU TOTAL'),('normal', 'Normal'), ('normal_d', 'Normal déclaré') ])
    customer_profil = fields.Selection(string='Profil client',selection=[('on', 'ON-US'),('off', 'OFF-US'), ])
    #payment_mode = fields.Selection(string='Mode de paiement', selection=[('espece', 'Espèce'), ('check', 'Chèque/Virement'), ])
    airsi = fields.Char(string='AIRSI')
    region_id = fields.Many2one(comodel_name='region.region', string='Region')
    city_id = fields.Many2one(comodel_name='city.city',string='Ville')
    area_id = fields.Many2one(comodel_name='area.area',string='Zone')
    common_id = fields.Many2one(comodel_name='common.common',string='Commune')
    num_registre = fields.Char(string='N° Registre du commerce')
    neighborhood_id = fields.Many2one(comodel_name='neighborhood.neighborhood',string='Quartier')
    supplier_type = fields.Selection(string='Catégorie Fournisseur',selection=[('national', 'National'), ('international', 'International'), ])
    delivery_person = fields.Boolean(string='Livreur', default=False)


    

class Family(models.Model):
    _name = 'family.custom'
    _description = 'Famille de client'

    name = fields.Char(string='Famille client')

class Region(models.Model):
    _name = 'region.region'
    _description = 'Region'

    name = fields.Char(string='Région',required=True)
    city_ids = fields.One2many(comodel_name='city.city', inverse_name='region_id',string="Ville")  
    
class City(models.Model):
    _name = 'city.city'
    _description = 'Ville'

    name = fields.Char(string='Ville',required=True)
    region_id = fields.Many2one(comodel_name='region.region',required=True,string='Region')
    area_ids = fields.One2many(comodel_name='area.area', inverse_name='city_id',string="Zone") 

class Area(models.Model):
    _name = 'area.area'
    _description = 'Zone'

    name = fields.Char(string='Zone',required=True)
    city_id = fields.Many2one(comodel_name='city.city',string='Ville',required=True)
    common_ids = fields.One2many(comodel_name='common.common', inverse_name='area_id',string="Commune",) 

    

class Common(models.Model):
    _name = 'common.common'
    _description = 'Commune'

    name = fields.Char(string='Commune',required=True)
    area_id = fields.Many2one(comodel_name='area.area',string='Zone',required=True,)
    neighborhood_ids = fields.One2many(comodel_name='neighborhood.neighborhood', inverse_name='common_id',string="Quartier") 


class Neighborhood(models.Model):
    _name = 'neighborhood.neighborhood'
    _description = 'Quartier'

    name = fields.Char(string='Quartier',required=True)
    common_id = fields.Many2one(comodel_name='common.common',string='Commune',required=True,)