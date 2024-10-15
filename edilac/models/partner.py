from odoo import models, fields, api
from datetime import datetime


class Partner(models.Model):
    _inherit = 'res.partner'


    date_create_customer =fields.Datetime(string='Date Création client', default=fields.Datetime.now)
    family_cust = fields.Many2one(comodel_name='family.custom',string='Famille client')
    customer_type = fields.Selection(string='Type de client',selection=[('tva', 'TVA OU TOTAL'),('normal', 'Normal'), ])
    custom_profil = fields.Char(string='Profil client')
    payment_mode = fields.Selection(string='Mode de paiement',
                                     selection=[('espece', 'Espèce'), ('check', 'Chèque/Virement'), ])
    airsi = fields.Char(string='AIRSI')
    #vendor = fields.Many2one(comodel_name='res.partner',related='user_id.name', string='Vendeur')
    common = fields.Char(string='Commune')
    day_visit = fields.Integer(string='Jours visite')

    supplier_type = fields.Selection(string='Type de fournisseur',
                                     selection=[('national', 'National'), ('international', 'International'), ])




class Family(models.Model):
    _name = 'family.custom'
    _description = 'Famille de client'

    name = fields.Char(string='Famille client')