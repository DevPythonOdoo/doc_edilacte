# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    as_a_salesperson = fields.Boolean('Comme un commercial')
    invoiced_target = fields.Monetary(string="Objectif de facturation")

    # invoiced_target = fields.Float(string="Objectif de facturation")
    target_ids = fields.One2many(
        string=_('Objectifs Commercial'),
        comodel_name='saleman.line',
        inverse_name='user_id',
    )
    customers_ids = fields.One2many(
        string=_('Clients suivi'),
        comodel_name='res.partner',
        inverse_name='user_id',
    )
   
    target_amount = fields.Monetary(string="Montant objectif",compute='_compute_amount',store=True)
    currency_id = fields.Many2one('res.currency', string="Devise",default=lambda self: self.env.company.currency_id)
    real_amount = fields.Monetary(string="Montant réel",compute='_compute_amount',store=True)
    percentage = fields.Float(string="Pourcentage d'atteinte", store=True, compute='_compute_amount')
    
    @api.depends('target_ids')
    def _compute_amount(self):
        for record in self:
            record.target_amount = sum(line.target_amount for line in record.target_ids)
            record.real_amount = sum(line.real_amount for line in record.target_ids)
            if record.target_amount:
                record.percentage = (record.real_amount / record.target_amount) * 100 if record.target_amount else 0.0
            

class SalemLine(models.Model):
    _name = 'saleman.line'
    _description = _('Objectif Commercial')
    _order = 'date_start desc'
    
    date_start = fields.Datetime(string="Date début",required=True)
    date_end = fields.Datetime(string="Date fin",required=True)
    target_amount = fields.Monetary(string="Montant objectif")
    currency_id = fields.Many2one('res.currency', string="Devise",default=lambda self: self.env.company.currency_id)
    real_amount = fields.Monetary(string="Montant réel",compute='_compute_real_amount',store=True)
    percentage = fields.Float(string="Pourcentage d'atteinte",compiled=True, store=True, compute='_compute_percentage')
    user_id = fields.Many2one('res.users', string="Commercial")
    line_ids = fields.One2many(
        string=_('Commande Client'),
        comodel_name='sale.order',
        inverse_name='user_id',domain=[('state','in',('sale','done'))])

    @api.onchange('date_start', 'date_end')
    def _onchange_date_start_end(self):
        data = []
        self.update({'line_ids': []})
        if self.date_start and self.date_end and self.date_start > self.date_end:
            raise ValidationError(_('La date de début doit être antérieure à la date de fin.'))
        for record in self:
            for line in record.line_ids.filtered(lambda order: order.date_order >= record.date_start and order.date_order <= record.date_end):
                data.append(line.id)
            # raise ValidationError(data)
            record.line_ids = [(6, 0, data)]
       
    @api.depends('real_amount', 'target_amount')
    def _compute_percentage(self):
        for record in self:
            record.percentage = (record.real_amount / record.target_amount) * 100 if record.target_amount else 0.0
    @api.depends('line_ids.amount_total')
    def _compute_real_amount(self):
        total_amount = 0.0
        for record in self:
            if record.line_ids.filtered(lambda order: order.state in ('sale','done')):
                for line in record.line_ids.filtered(lambda order: order.date_order >= record.date_start and order.date_order <= record.date_end):
                    total_amount += line.amount_total
                # raise ValidationError(total_amount)
                record.real_amount = total_amount



class CrmTeam(models.Model):
    _inherit = 'crm.team'

    @api.model
    def write(self, vals):
        # Sauvegarder les utilisateurs actuels avant la mise à jour
        previous_members = self.member_ids
        # Appeler la méthode write pour effectuer la mise à jour
        res = super(CrmTeam, self).write(vals)
        # Récupérer les nouveaux membres après la mise à jour
        current_members = self.member_ids
        # Activer as_a_salesperson pour les utilisateurs ajoutés
        for user in current_members:
            if user not in previous_members:
                user.as_a_salesperson = True
        # Désactiver as_a_salesperson pour les utilisateurs supprimés
        for user in previous_members:
            if user not in current_members:
                user.as_a_salesperson = False

        return res


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    region_id = fields.Many2one(comodel_name='region.region', string='Region',related="partner_id.region_id",store=True)
    city_id = fields.Many2one(comodel_name='city.city',string='Ville',related="partner_id.city_id",store=True)
    area_id = fields.Many2one(comodel_name='area.area',string='Zone',related="partner_id.area_id",store=True)
    common_id = fields.Many2one(comodel_name='common.common',string='Commune',related="partner_id.common_id",store=True)
    family_cust = fields.Many2one(comodel_name='family.custom',string='Famille client',related="partner_id.family_cust",store=True)
    neighborhood_id = fields.Many2one(comodel_name='neighborhood.neighborhood',string='Quartier',related="partner_id.neighborhood_id",store=True)
    @api.model
    def create(self, vals):
        # Récupérer le partenaire et son type de client
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        prefix = 'S'  # Préfixe par défaut

        # Modifier le préfixe en fonction du type de client
        if partner.customer_type == 'tva':
            prefix = 'T'
        elif partner.customer_type == 'normal':
            prefix = 'N'
        elif partner.customer_type == 'normal_d':
            prefix = 'ND'

        # Générer le numéro de séquence en utilisant le préfixe personnalisé
        seq = self.env['ir.sequence'].next_by_code('sale.order') or '/'
        vals['name'] = prefix + seq[1:]  # Remplace le premier caractère par le préfixe désiré

        # Appeler la méthode create parente
        return super(SaleOrder, self).create(vals)
    
    from odoo import models, fields, api, _
    
    
class saleOderLine(models.Model):
    _inherit = 'sale.order.line'

    date_order = fields.Datetime(string=_('Date Commande'), related='order_id.date_order',store=True,precompute=True)
    partner_type = fields.Selection(related='order_partner_id.customer_type', string=_('Type de client'),store=True,precompute=True)
    invoice_status = fields.Selection(related='order_id.invoice_status', string=_('Etat de facturation'),store=True,precompute=True)
    
    