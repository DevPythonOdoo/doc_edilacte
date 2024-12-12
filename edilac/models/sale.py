# -*- coding: utf-8 -*-
import logging
from odoo.tools import config

from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    as_a_salesperson = fields.Boolean('Comme un commercial')
    invoiced_target = fields.Monetary(string="Objectif de facturation")

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

    target_amount = fields.Monetary(string="Montant dernier objectif",related="target_ids.target_amount",store=True)
    currency_id = fields.Many2one('res.currency', string="Devise",default=lambda self: self.env.company.currency_id)
    real_amount = fields.Monetary(string="Dernier CA",related="target_ids.real_amount",store=True)
    percentage = fields.Float(string="Pourcentage d'atteinte",compiled=True, store=True, compute='_compute_percentage')

    @api.depends('real_amount', 'target_amount')
    def _compute_percentage(self):
        for record in self:
            record.percentage = (record.real_amount / record.target_amount) * 100 if record.target_amount else 0.0

class SalemLine(models.Model):
    _name = 'saleman.line'
    _description = _('Objectif Commercial')
    _order = 'date_start desc'
    
    date_start = fields.Date(string="Date début objectif")
    date_end = fields.Date(string="Date fin objectif")
    start_period = fields.Date(string="Date début")
    end_period = fields.Date(string="Date fin")
    target_amount = fields.Monetary(string="Montant objectif",)
    currency_id = fields.Many2one('res.currency', string="Devise",default=lambda self: self.env.company.currency_id)
    real_amount = fields.Monetary(string="Montant réel",store=True, compute='_compute_real_amount')
    percentage = fields.Float(string="Pourcentage d'atteinte", store=True, compute='_compute_percentage')
    user_id = fields.Many2one('res.users', string="Commercial")
    lines_ids = fields.One2many(
        string=_('Prévision Commerciale'),
        comodel_name='business.forecast',
        inverse_name='saleman_id')
    
    @api.depends('lines_ids')
    def _compute_percentage(self):
        for record in self:
            record.percentage = sum(line.percentage for line in record.lines_ids)
    
    @api.depends('lines_ids')
    def _compute_real_amount(self):
        for record in self:
            record.real_amount = sum(line.amount for line in record.lines_ids)



                
    def forecast_confirm(self):
        data = []
        for record in self:
            if record.target_amount == 0 : 
                raise UserError("Veuillez saisir un montant objectif.")
            result = self.env['sale.order'].calculate_market_share(record.user_id,record.start_period,record.end_period, record.target_amount)
            if result :
                if record.lines_ids:
                    # Supprimer les lignes existantes
                    record.lines_ids.unlink()
                # Afficher les résultats
                for client_id, market_share in result.items():
                    orders = self.env['sale.order'].search([('user_id', '=', record.user_id.id), ('state', 'in', ('sale','done')),
                    ('partner_id', '=', client_id),('date_order', '>=', record.date_start), ('date_order', '<=', record.date_end)])
                    self.env['business.forecast'].create({
                        'saleman_id': record.id,
                        'ca': market_share[1],
                        'forecast_amount': round(market_share[0], 2) * 100 ,
                        'target_amount': round(market_share[0], 2) * record.target_amount,
                        'partner_id': client_id,
                        'amount': sum(order.amount_total for order in orders),
                    })
        # self.env['business.forecast'].create(data)
        return True
                  
class BusinessForecast(models.Model):
    _name = 'business.forecast'
    _description = _('business.forecast')

    saleman_id = fields.Many2one(
        string=_('Commercial'),
        comodel_name='saleman.line', ondelete='cascade',
    )
    forecast_amount = fields.Float(string=_('Prévision %'))
    target_amount = fields.Monetary(string="Part de Marché")
    ca = fields.Monetary(string="Chiffre d'affaires")
    currency_id = fields.Many2one('res.currency', string="Devise",default=lambda self: self.env.company.currency_id)
    percentage = fields.Float(string="Pourcentage d'atteinte", store=True, compute='_compute_percentage')
    amount = fields.Monetary(string="Montant réel")
    partner_id = fields.Many2one("res.partner", string=_('Client'),required=True)
    date_start = fields.Date(string="Date début",related='saleman_id.date_start',store=True)
    date_end = fields.Date(string="Date fin",related='saleman_id.date_end',store=True)
    

    @api.depends('amount', 'target_amount')
    def _compute_percentage(self):
        for record in self:
            record.percentage = (record.amount / record.target_amount) * 100 if record.target_amount else 0.0
        

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

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    pricelist_id = fields.Many2one(comodel_name='product.pricelist', string='Liste de prix')
    region_id = fields.Many2one(comodel_name='region.region', string='Region')
    city_id = fields.Many2one(comodel_name='city.city',string='Ville')
    area_id = fields.Many2one(comodel_name='area.area',string='Zone')
    common_id = fields.Many2one(comodel_name='common.common',string='Commune')
    neighborhood_id = fields.Many2one(comodel_name='neighborhood.neighborhood',string='Quartier',required=True)
    industry_id = fields.Many2one(comodel_name='res.partner.industry',string="Secteur d'activité")
    customer_type_id = fields.Many2one(comodel_name='customer.type', string='Type de client')
    #customer_type = fields.Selection(string='Type de client', selection=[('tva', 'TVA OU TOTAL'), ('normal', 'Normal'),('normal_d', 'Normal déclaré')])
    customer_profil = fields.Selection(string='Profil client', selection=[('on', 'ON-US'), ('off', 'OFF-US')])
    company_type = fields.Selection(string='Type', selection=[('person', 'Particulier'), ('company', 'Societé')])
    is_won = fields.Boolean(string='Gagné', default=False)
    latitude = fields.Float("Latitude", digits=(10, 6))
    longitude = fields.Float("Longitude", digits=(10, 6))

    @api.model
    def capture_position(self, record_id, coordinates):
        # Vérifier si coordinates est un dictionnaire et contient les clés nécessaires
        if not isinstance(coordinates, dict) or 'latitude' not in coordinates or 'longitude' not in coordinates:
            raise ValidationError("Les coordonnées doivent contenir 'latitude' et 'longitude'.")

        # Rechercher l'enregistrement correspondant
        lead = self.browse(record_id)
        if lead.exists():
            lead.write({
                'latitude': coordinates['latitude'],
                'longitude': coordinates['longitude'],
            })
            return True  # Retourne True pour indiquer que la mise à jour a réussi.
        else:
            raise ValidationError(f"L'enregistrement avec l'ID {record_id}n'existe pas.")
        
    @api.onchange('neighborhood_id')
    def _onchange_neighborhood_id(self):
        """Cette fonction permet de sélectionner le quartier et de renvoyer la commune, la région, la zone et la ville"""
        if self.neighborhood_id:
            # Mise à jour des autres champs en fonction du quartier sélectionné
            self.common_id = self.neighborhood_id.common_id
            self.area_id = self.common_id.area_id
            self.city_id = self.area_id.city_id
            self.region_id = self.city_id.region_id
        else:
            # Réinitialisation des champs si aucun quartier n'est sélectionné
            self.common_id = False
            self.area_id = False
            self.city_id = False
            self.region_id = False

    def action_set_won(self):
        """ Won semantic: probability = 100 (active untouched) """
        self.action_unarchive()
        # group the leads by team_id, in order to write once by values couple (each write leads to frequency increment)
        leads_by_won_stage = {}
        for lead in self:
            if not lead.customer_profil:
                raise UserError("Veuillez renseigner le profil client.")
            if not lead.customer_type_id:
                raise UserError("Veuillez renseigner le type de client.")
            if not lead.industry_id:
                raise UserError("Veuillez renseigner le secteur d'activité.")
            if not lead.pricelist_id:
                raise UserError("Veuillez renseigner la liste de prix.")
            

            values = {
                'property_product_pricelist': lead.pricelist_id.id,
                'user_id': lead.user_id.id,
                'region_id': lead.region_id.id,
                'city_id': lead.city_id.id,
                'area_id': lead.area_id.id,
                'common_id': lead.common_id.id,
                'neighborhood_id': lead.neighborhood_id.id,
                'customer_type_id': lead.customer_type_id.id,
                'customer_rank': 10,
                'customer_profil': lead.customer_profil,
                'industry_id': lead.industry_id.id,
                'name':lead.contact_name,
                'phone': lead.phone,
                'mobile': lead.mobile,
                'company_type': lead.company_type,
                'partner_longitude': lead.longitude,
                'partner_latitude': lead.latitude,
            }
            partner_id = self.env['res.partner'].create(values)
            won_stages = self._stage_find(domain=[('is_won', '=', True)], limit=None)

            stage_id = next((stage for stage in won_stages if stage.sequence > lead.stage_id.sequence), None)
            if not stage_id:
                stage_id = next((stage for stage in reversed(won_stages) if stage.sequence <= lead.stage_id.sequence), won_stages)
            if stage_id in leads_by_won_stage:
                leads_by_won_stage[stage_id] += lead
            else:
                leads_by_won_stage[stage_id] = lead
        for won_stage_id, leads in leads_by_won_stage.items():
            leads.write({'stage_id': won_stage_id.id, 'probability': 100,'partner_id':partner_id.id,'is_won': True})
        return True

    def action_location_gps(self):
        geo_obj = self.env['base.geocoder']
        for lead in self:
            # Crée l'adresse à partir des champs de l'opportunité
            address = geo_obj.geo_query_address(
                street=lead.street,
                zip=lead.zip,
                city=lead.city,
                state=lead.state_id.name if lead.state_id else '',
                country=lead.country_id.name if lead.country_id else ''
            )
            # Récupère les coordonnées via le géocodeur
            result = geo_obj.geo_find(address)
            if result:
                lead.latitude = result[0]
                lead.longitude = result[1]
            else:
                raise UserError(_("Aucune géolocalisation trouvée pour l'adresse: %s.") % address)

    @api.model
    def _geo_localize(self, street='', zip='', city='', state='', country=''):
        geo_obj = self.env['base.geocoder']
        search = geo_obj.geo_query_address(street=street, zip=zip, city=city, state=state, country=country)
        result = geo_obj.geo_find(search, force_country=country)
        if result is None:
            search = geo_obj.geo_query_address(city=city, state=state, country=country)
            result = geo_obj.geo_find(search, force_country=country)
        return result

    def geo_localize(self):
        # We need country names in English below
        if not self._context.get('force_geo_localize') \
                and (self._context.get('import_file') \
                     or any(config[key] for key in ['test_enable', 'test_file', 'init', 'update'])):
            return False
        partners_not_geo_localized = self.env['res.partner']
        for partner in self.with_context(lang='en_US'):
            result = self._geo_localize(partner.street,partner.zip,partner.city, partner.state_id.name,partner.country_id.name)
            if result:
                partner.write({
                    'partner_latitude': result[0],
                    'partner_longitude': result[1],
                    'date_localization': fields.Date.context_today(partner)
                })
            else:
                partners_not_geo_localized |= partner
        if partners_not_geo_localized:
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'danger',
                'title': _("Warning"),
                'message': _('Aucune correspondance trouvée pour %(partner_names)s address(es).', partner_names=', '.join(partners_not_geo_localized.mapped('name')))
            })
        return True
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    common_id = fields.Many2one(related='partner_id.common_id', string='Commune', store=True)
    neighborhood_id = fields.Many2one(related='partner_id.neighborhood_id', string='Quartier', store=True)
    area_id = fields.Many2one(related='partner_id.area_id', string='Zone', store=True)
    amount_paid = fields.Float(string="Montant Payé", compute='_compute_invoice_amounts', store=True)
    amount_delivery = fields.Float(string="Montant facturé", compute='_compute_invoice_amounts', store=True)
    amount_due = fields.Float(string="Créances", compute='_compute_invoice_amounts', store=True)
    qty_delivered = fields.Float(string="Qty Livré",store=True, readonly=False, copy=False,compute="_compute_total_qty_line")
    product_uom_qty = fields.Float(string="Qty Commandé",store=True, readonly=False,compute="_compute_total_qty_line",)
    qty_return = fields.Float(string=_('Qty retourné'), store=True, readonly=True, compute="_compute_total_qty_line")
    nbm_pc_crt = fields.Float(string='Nbre de pc/carton',store=True, required=False,compute="_compute_total_qty_line")
    customer_invoice_ids = fields.One2many(comodel_name='account.move', inverse_name='sale_id',string='Facture Client',domain=[('move_type', '=', 'out_invoice')], required=False)

    customer_invoice_count = fields.Integer(string="'Nombre de facture", required=False,compute="_compute_customer_invoice_count", store=True)

    def action_create_draft_invoice(self):
        """Crée une facture client en brouillon pour la commande."""
        for order in self:
            if order.state not in ['sale', 'done']:
                raise ValueError("Vous ne pouvez facturer qu'une commande confirmée.")

            # Crée une facture en brouillon
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': order.partner_id.id,
                'invoice_origin': order.name,
                'currency_id': order.currency_id.id,
                'invoice_line_ids': [],
                'sale_id': self.id,
            }

            # Ajouter les lignes de facturation
            for line in order.order_line:
                invoice_line_vals = {
                    'product_id': line.product_id.id,
                    'quantity': line.move_ids.quantity,
                    'price_unit': line.price_unit,
                    'name': line.name,
                    'tax_ids': [(6, 0, line.tax_id.ids)],
                }
                invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

            # Créer le brouillon
            invoice = self.env['account.move'].create(invoice_vals)

            # Optionnel : Lier la facture à la commande
            order.write({'invoice_ids': [(4, invoice.id)]})

        return True
    @api.depends('customer_invoice_ids')
    def _compute_customer_invoice_count(self):
        for rec in self:
            rec.customer_invoice_count = len(rec.customer_invoice_ids)

    def button_open_customer_invoice_count(self):
        return {

            'name': 'Facture Client',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'context': {'edit': False, 'create': False},
            'domain': [('sale_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

 

    @api.constrains('order_line.product_id')
    def _check_order_stock(self):
        for order in self:
            for line in order.order_line:
                if line.product_id.type == 'product':  # Vérifier uniquement les produits stockés
                    available_qty = line.product_id.qty_available
                    if line.product_uom_qty > available_qty:
                        raise ValidationError(
                            f"Le produit '{line.product_id.display_name}' dans la commande {order.name} "
                            f"n'a pas assez de stock disponible (Stock actuel : {available_qty}, demandé : {line.product_uom_qty})."
                        )

    @api.depends('order_line.product_uom_qty','order_line.qty_delivered','order_line.qty_return')
    def _compute_total_qty_line(self):
        for order in self:
            order.product_uom_qty = sum(order.order_line.mapped('product_uom_qty'))
            order.qty_delivered = sum(order.order_line.mapped('qty_delivered'))
            order.qty_return = sum(order.order_line.mapped('qty_return'))
            order.nbm_pc_crt = sum(order.order_line.mapped('nbr_pc_crt'))


    def calculate_market_share(self, commercial_id,start_date,end_date, total_market_revenue):
        """
        Calcule la part de marché d'un commercial donné.

        :param commercial_id: ID du commercial (res.users.id)
        :param total_market_revenue: Chiffre d'affaires total du marché (float)
        :param months: Nombre de mois pour l'analyse (int)
        :return: Dictionnaire avec la part de marché par client
        """
        if not total_market_revenue:
            raise ValueError("Le chiffre d'affaires total du marché doit être fourni.")

      
        # Récupération des commandes du commercial
        sale_orders = self.env['sale.order'].search([
            ('user_id', '=', commercial_id.id),
            ('date_order', '>=', start_date),
            ('date_order', '<=', end_date),
            ('state', 'in', ['sale', 'done'])  # Seulement les commandes confirmées
        ])

        # Calcul du chiffre d'affaires par client
        client_revenue = {}
        total = 0
        for order in sale_orders:
            client = order.partner_id
            client_revenue[client.id] = client_revenue.get(client.id, 0) + order.amount_total
            total += order.amount_total

        # Calcul de la part de marché pour chaque client
        market_share = {}
        for client_id, revenue in client_revenue.items():
            market_share[client_id] = [(revenue / total),revenue ]
        return market_share
    
    def _prepare_confirmation_values(self):
        """ Prepare the sales order confirmation values.

        Note: self can contain multiple records.

        :return: Sales Order confirmation values
        :rtype: dict
        """

        return {
            'state': 'sale',
            # 'date_order': fields.Datetime.now()
        }
    def action_confirm(self):
        # Appeler la méthode action_confirm parente
        res = super(SaleOrder, self).action_confirm()
        for record in self:
            for forecast in record.partner_id.forecast_ids.filtered(lambda f:  f.date_start >= record.date_order.date() and f.date_end <= record.date_order.date()):
                forecast.write({'amount': forecast.amount + record.amount_total})
                raise UserError(f"Erreur : {forecast.amount} - {forecast.date_start} - {forecast.date_end} - {record.date_order}")
        return res

    @api.depends('customer_invoice_ids.payment_state', 'customer_invoice_ids.amount_residual','order_line.qty_delivered')
    def _compute_invoice_amounts(self):
        """
        Cette fonction permet de calculer les montants facturés, les créances et les quantités livrées dans le module !
        :return:
        """
        for order in self:
            paid_amount = 0.0
            total_untaxed = 0.0
            # Calcul du montant de livraison en prenant en compte la quantité livrée, le prix unitaire et les taxes
            delivery_amount = 0.0
            for line in order.order_line:
                if line.qty_delivered > 0:  # Assurez-vous que la quantité est livrée
                    # Calcul du montant avant taxe (prix unitaire * quantité livrée)
                    line_total = line.qty_delivered * line.price_unit
                    # Calcul des taxes pour la ligne (on prend le taux de taxe pour chaque ligne)
                    tax_amount = 0.0
                    for tax in line.tax_id:
                        # Calcul du montant des taxes appliquées à cette ligne
                        tax_amount += tax.compute_all(line.price_unit, order.currency_id, line.qty_delivered)['total_included'] - line_total
                    # Montant total de livraison (prix avant taxe + taxe)
                    delivery_amount += line_total + tax_amount
            # Parcourir toutes les factures liées à la commande
            for invoice in order.customer_invoice_ids.filtered(lambda inv: inv.state == 'posted'):
                # Accumuler le montant payé
                paid_amount += invoice.amount_paid  # Champ amount_paid contient le montant payé sur la facture
            # Montants calculés
            order.amount_delivery = delivery_amount
            order.amount_paid = paid_amount
            order.amount_due = order.amount_delivery - paid_amount

    @api.model
    def create(self, vals):
        # Récupérer le partenaire et son type de client
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        prefix = 'S'  # Préfixe par défaut
        seq = ""

        # Modifier le préfixe en fonction du type de client
        if partner.customer_type_id == 'tva':
            prefix = 'T'
            seq = self.env['ir.sequence'].next_by_code('sale.order') or '/'
        elif partner.customer_type_id in ('normal','normal_d') :
            prefix = 'N'
            seq = self.env['ir.sequence'].next_by_code('sale.order.normal') or '/'


        # Générer le numéro de séquence en utilisant le préfixe personnalisé
        vals['name'] = prefix + seq[1:]  # Remplace le premier caractère par le préfixe désiré

        # Appeler la méthode create parente
        return super(SaleOrder, self).create(vals)
   
class saleOderLine(models.Model):
    _inherit = 'sale.order.line'

    date_order = fields.Datetime(string=_('Date Commande'), related='order_id.date_order',store=True,precompute=True)
    partner_type_id = fields.Many2one(related='order_partner_id.customer_type_id', string=_('Type de client'),store=True,precompute=True)
    invoice_status = fields.Selection(related='order_id.invoice_status', string=_('Etat de facturation'),store=True,precompute=True)
    qty_return = fields.Float(string=_('Qty retourné'),compute='_compute_qty_return', store=True, readonly=True)
    product_id = fields.Many2one(comodel_name='product.product',string='Produit',required=False)
    nbr_pc_crt = fields.Float(related='product_id.nbm_pc_crt',string='Nbre de pc/carton',store=True)

    @api.onchange('product_id', 'product_uom_qty')
    def _check_product_stock(self):
        for line in self:
            if line.product_id.type == 'product':  # Vérifier uniquement les produits stockés (pas les services)
                available_qty = line.product_id.qty_available
                if line.product_uom_qty > available_qty:
                    raise ValidationError(
                        f"Le produit '{line.product_id.display_name}' n'a pas assez de stock disponible "
                        f"(Stock actuel : {available_qty}, demandé : {line.product_uom_qty})."
                    )

    @api.depends('product_uom_qty', 'qty_delivered')
    def _compute_qty_return(self):
        for line in self:
            if line.qty_delivered > 0:
                line.qty_return = line.product_uom_qty - line.qty_delivered
class producpricelist(models.Model):
    _inherit = 'product.pricelist'

    state = fields.Selection(
        string=_('state'),
        selection=[
            ('draft', 'Nouveau'),
            ('send', 'Soumis'),
            ('done', 'Validé'),
        ], default='draft', readonly=True, tracking=True,
    )

    def action_submit(self):
        # for rec in self:
        #     if not rec.item_ids:
        #         raise exceptions.UserError('Veuillez ajouter des règles de tarification pour cette liste de prix.')
        self.write({"state": "send"})

    def action_validate(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "draft"})


class AccountMove(models.Model):
    _inherit = 'account.move'

    amount_paid = fields.Float(string="Montant Payé", compute='_compute_invoice_amounts', store=True)
    sale_id = fields.Many2one(comodel_name='sale.order', string='Facture Client', required=False, tracking=True)

    @api.depends('payment_state', 'amount_total', 'amount_residual')
    def _compute_invoice_amounts(self):
        for invoice in self:
            invoice.amount_paid = invoice.amount_total - invoice.amount_residual


class ProductProduct(models.Model):
    _inherit = 'product.product'

    nbm_pc_crt = fields.Float(string='Nbre de pc/carton', required=False)