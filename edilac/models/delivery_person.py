from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class Product(models.Model):
    _name = 'delivery.person'
    _description = 'Livreur'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Nom", reqired=True)
    mail = fields.Char("Email", reqired=True)
    phone = fields.Char("Téléphone", reqired=True)
    adress = fields.Char("Adress", reqired=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Société', required=True,
                                default=lambda self: self.env.company.id)
    user_id=fields.Many2one(comodel_name='res.users', string='Utilisateur lié', required=True)
    