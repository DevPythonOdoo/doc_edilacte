# -*- coding: utf-8 -*-
import logging
try:
    import qrcode
except ImportError:
    qrcode = None
try:
    import base64
except ImportError:
    base64 = None
from io import BytesIO

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = 'product.product'

    capacity = fields.Float(string='Capacité du congélateur', required=False, help="Une fois coché, le produit sera marqué comme un congélateur")
    freezer = fields.Boolean(string='Marqué Comme un Congélateur', related="product_tmpl_id.freezer",store=True)


class PartnerFreezer(models.Model):
    _name = 'partner.freezer'
    _description = 'Congélateur lié au client'

    product_id = fields.Many2one('product.product', string="Nom du Congélateur", domain=[('freezer', '=', True)],
                                 help="Sélectionner un produit marqué comme congélateur")
    capacity = fields.Float(related='product_id.capacity',store=True, string="Capacité", help="Capacité du congélateur en litres")
    partner_id = fields.Many2one('res.partner', string="Client", ondelete='cascade')
    freezer_number = fields.Integer(string="Nombre de Congélateur", default=1)
    turnover = fields.Float(string="Chiffre d'affaire")



class FreezerAssignment(models.Model):
    _name = 'freezer.assignment'
    _description = 'Freezer Assignment'
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence Affecation', required=False, copy=False, readonly=True,default="Nouveau")
    customer_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True)
    customer_number = fields.Char(related='customer_id.ref', string='Téléphone', readonly=True)
    customer_email = fields.Char(related='customer_id.email', string='Email', readonly=True)
    # caution = fields.Float(string='Caution', readonly=False,tracking=True)
    company_id = fields.Many2one('res.company', string='Société', required=False, default=lambda self: self.env.company, tracking=True)
    lot_id = fields.Many2one(comodel_name='stock.lot',string='N° de série', required=False,  tracking=True)
    product_id = fields.Many2one('product.product', string='Congélateur', required=True)
    date = fields.Date(string='Date Déploiement', required=True, default=fields.Date.today)
    qr = fields.Binary(string="QR Code", help='Used for Qr code')
    sequence = fields.Char(string="QR Sequence", readonly=True)
    state = fields.Selection([
        ('new', 'Nouveau'),
        ('adv', 'En attente'),
        ('stock_management', 'Déploiement'),
        ('done', 'Fait'),
        ('cancel', 'Annuler')
    ], string='Statut', default='new', tracking=True)

    customer_contract_ids = fields.One2many(comodel_name='customer.contract',inverse_name='freezer_id',string='Contrat client',required=False)
    contract_state = fields.Selection(related='customer_contract_ids.state', string='Statut du contrat', store=True)

    customer_contract_count = fields.Integer(
        string='Nombre de contrats clients',
        required=False, compute="_compute_customer_contract_count", store=True)

    customer_delivery_ids = fields.One2many(comodel_name='stock.picking', inverse_name='delivery_id',
                                            string='Livraison Client', required=False)

    customer_delivery_count = fields.Integer(
        string='Nombre de Livraison',
        required=False, compute="_compute_customer_delivery_count", store=True)


    company_id = fields.Many2one(
        string=_('Societé'), 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company
    )

    @api.model
    def trigger_field_visit_action(self):
        print('ok je suis là')
        action = self.env.ref('edilac.action_field_visit_wizard').read()[0]
        action['context'] = {'default_freezer_assignment_id': self.id}
        action['target'] = 'new'  # Ouvre la vue dans une nouvelle fenêtre
        return action

    def qr_print(self):
        """Print the QR code."""
        for record in self:
            if not record.qr:
                raise UserError(_('No QR code to print. Please generate a QR code first.'))
            return self.env.ref('edilac.print_qr').report_action(self, data={ 'data': self.id, 'type': 'cust'})
                
    def generate_qr(self):
        """Generate a QR code based on the partner's sequence and store it in
        the 'qr' field of the partner record."""
        for record in self:
            if qrcode and base64:
                record.sequence = str(record.customer_id.name) + " " + str(record.lot_id.name)
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(self.sequence)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                self.write({'qr': qr_image})
                
            else:
                raise UserError(
                    _('Necessary Requirements To Run This Operation Is Not '
                    'Satisfied'))

    @api.model
    def create(self, vals):
        res = super(FreezerAssignment, self).create(vals)
        res.name = self.env['ir.sequence'].next_by_code('freezer.assignment')
        return res


    def button_open_customer_contract(self):
        return {

            'name': 'Contrats clients',
            'res_model': 'customer.contract',
            'view_mode': 'list,form',
            'context': {'edit': False, 'create': False},
            'domain': [('freezer_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

    def button_open_customer_delivery(self):
        return {

            'name': 'Livraison Client',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'context': {'edit': False, 'create': False},
            'domain': [('delivery_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

    @api.depends('customer_contract_ids')
    def _compute_customer_contract_count(self):
        for rec in self:
            rec.customer_contract_count = rec.env['customer.contract'].search_count([('freezer_id', '=', rec.id)])

    @api.depends('customer_delivery_ids')
    def _compute_customer_delivery_count(self):
        for rec in self:
            rec.customer_delivery_count = len(rec.customer_delivery_ids)

    # Fonction qui récupère les numéros de série depuis stock.move
    @api.model
    def _get_freezer_serial_numbers(self):
        """Récupère les numéros de série des produits marqués comme congélateurs via stock.move,
        avec une quantité disponible d'au moins 1.
        """
        freezer_products = self.env['product.product'].search([('freezer', '=', True)])
        serial_numbers = []
        for product in freezer_products:
            # Recherche des mouvements de stock associés au produit
            moves = self.env['stock.move'].search([('product_id', '=', product.id), ('state', '=', 'done')])
            for move in moves:
                if move.lot_ids:
                    for lot in move.lot_ids:
                        # Vérification de la quantité disponible pour ce numéro de série (lot)
                        quant = self.env['stock.quant'].search([
                            ('lot_id', '=', lot.id),
                            ('quantity', '>=', 1),
                            ('location_id.usage', '=', 'internal'),  # Emplacement interne uniquement
                        ], limit=1)

                        if quant:
                            serial_numbers.append(lot.name)

        return serial_numbers or [('', 'Non défini')]


    def action_submit(self):
        self.write({'state': 'adv'})
        mail_template = self.env.ref('edilac.email_template_adv')
        mail_template.send_mail(self.id, force_send=True)

    def action_validate(self):
        self.action_approve()
        mail_template = self.env.ref('edilac.email_template_deploiement')
        mail_template.send_mail(self.id, force_send=True)
        self.generate_qr()
        return self.write({'state': 'stock_management'})

    def action_approve(self):
        """Créer un picking et un mouvement de stock pour la livraison du congélateur"""
        picking_type = self.env['stock.picking.type'].search([('is_free_transfer', '=', True),('company_id', '=', self.env.company.id)], limit=1
            )

        location_id = picking_type.default_location_src_id
        location_dest_id = picking_type.default_location_dest_id

        if not location_id:
            raise UserError("Aucun emplacement n'a pas été trouvé.")

        if not self.lot_id:
            raise UserError("Veuillez selectionner un numéro de série.")


        picking = self.env['stock.picking'].create({
            'partner_id': self.customer_id.id,
            'picking_type_id': picking_type.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'origin': self.name,
            'delivery_id': self.id,
        })

        stock_move = self.env['stock.move'].create({
            'name': f'Affectation de {self.product_id.name} au client {self.customer_id.name}',
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_id.id,
            'product_uom_qty': 1,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'picking_id': picking.id,
        })
        # stock_move.write({'lot_ids': [(4, self.lot_id.id)]})

        # Créer la ligne de mouvement de stock sans spécifier 'qty_done'
        stock_move_line = self.env['stock.move.line'].create({
            'move_id': stock_move.id,
            'product_id': self.product_id.id,
            'lot_id': self.lot_id.id,
            'quantity': 1,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
        })


        picking.action_confirm()
        picking.action_assign()

        # Afficher une notification de succès
        return True

    def action_validate(self):
        self.action_approve()
        mail_template = self.env.ref('edilac.email_template_deploiement')
        mail_template.send_mail(self.id, force_send=True)
        self.generate_qr()
        return self.write({'state': 'stock_management'})

    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': 'Succès',
    #             'message': 'Un bon de Livraison a été créée avec succès pour le deploiement du congelateur de ce client.',
    #             'type': 'success',  # Types disponibles : 'success', 'warning', 'danger', 'info'
    #             'sticky': False,  # Si True, le message reste affiché
    #         }
    # }

    def action_done(self):
        # Changer l'état à 'done'
        self.write({'state': 'done'})

        # Générer un contrat client
        self._create_customer_contract()

    def _create_customer_contract(self):
        """Créer un contrat client lié à l'affectation."""
        CustomerContract = self.env['customer.contract']

        for record in self:
            # Vérifier si un contrat existe déjà pour cette affectation
            existing_contract = CustomerContract.search([('freezer_id', '=', record.id)], limit=1)
            if not existing_contract:
                # Créer un nouveau contrat client
                contract_vals = {
                    'name': f'Contrat-{record.name or "N/A"}',
                    'customer_id': record.customer_id.id,
                    'freezer_id': record.id,
                    'lot_id': record.id,
                    'date': fields.Date.today(),  # Contrat valide pour 1 an
                    'deposit_amount': 0.0,  # À remplir selon vos besoins
                    'transport_amount': 0.0,  # À remplir selon vos besoins
                    'freezer_capacity': record.product_id.volume or 0,
                    'company_id': record.company_id.id,
                }
                CustomerContract.create(contract_vals)



    def action_cancel(self):
        """
        in_consultation -> cancel
        @return:
        """
        for rec in self:
            rec.state = 'cancel'

    def action_new(self):
        """
        in_consultation -> cancel
        @return:
        """
        for rec in self:
            rec.state = 'new'

class CustomerContract(models.Model):
    _name = 'customer.contract'
    _description = 'Customer Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence Contract ', required=False, copy=False, readonly=True)
    customer_id = fields.Many2one('res.partner', string='Client', related='freezer_id.customer_id', required=True,tracking=True)
    freezer_id = fields.Many2one(comodel_name='freezer.assignment', string='Reference Affectation', required=False,tracking=True)
    state = fields.Selection([
        ('new', 'Nouveau'),
        ('approval', 'Approbation'),
        ('in_progress', 'En cours'),
        ('expired', 'Expiré'),
        ('done', 'Remoursée'),
        ('cancel', 'Annulé'),
    ], string='Contract Status', default='new',tracking=True)
    date = fields.Date(string='Date du Contrat',default= fields.Date.today, tracking=True)
    date_end = fields.Date(string="Date d'expiration", readonly=True,)

    customer_number = fields.Char(related='customer_id.ref', string='Téléphone', readonly=True)
    customer_email = fields.Char(related='customer_id.email', string='Email', readonly=True)
    num_registre = fields.Char(related='customer_id.vat', string='Numero Contribuable', readonly=True)
    # num_registre = fields.Char(string='N° Registre du commerce')
    area_id = fields.Many2one(related='customer_id.area_id', string='Zone', store=True)
    common_id = fields.Many2one(related='customer_id.common_id', string='Commune', store=True)
    lot_id = fields.Many2one("stock.lot", related='freezer_id.lot_id', string='Congélateur',  store=True)
    neighborhood_id = fields.Many2one(related='customer_id.neighborhood_id', string='Quartier', store=True)
    deposit_amount = fields.Monetary(string='Total Caution', required=False,tracking=True)
    deposit_amount_payment = fields.Monetary(string='Caution payée', readonly=True,tracking=True)
    deposit_amount_of = fields.Monetary(string='Montant Restant', required=False,tracking=True,compute='_compute_deposit_amount_of')
    transport_amount = fields.Monetary(string='Montant Transport', required=False,tracking=True)
    currency_id = fields.Many2one('res.currency', string='Devise', related='company_id.currency_id', store=True)
    payment_state = fields.Selection([('unpaid', 'Non payé'),('partial', 'Partiellement payé'),('paid', 'Payé'),
    ], string='Statut Paiement',  store=True, default='unpaid',compute='_compute_payment_state')
    freezer_capacity = fields.Float(string='Capacité du Congélateur',related='lot_id.product_id.capacity', required=False,tracking=True)
    company_id = fields.Many2one('res.company', string='Société', required=False, default=lambda self: self.env.company, tracking=True)
    # move_payment_id = fields.Many2one('account.move', string="Entrée comptable paiement", readonly=True)
    is_driver_paid = fields.Boolean(string=_('Transport payé'), default=False)
    payment_ids = fields.One2many(comodel_name='account.payment', inverse_name='paiement_id',string='Paiement Client', required=False)

    customer_paiement_count = fields.Integer(string='Nombre de Paiement',required=False, compute="_compute_customer_paiement_count", store=True)

    freezer_return_ids = fields.One2many(comodel_name='stock.picking', inverse_name='freezer_return_id',string='Retour Congélateur', required=False)
    freezer_return_count = fields.Integer(string='Nombre de Congélateur', required=False,
                                             compute="_compute_freezer_return_count", store=True)

    @api.depends('deposit_amount', 'deposit_amount_payment')
    def _compute_deposit_amount_of(self):
        for rec in self:
            rec.deposit_amount_of = rec.deposit_amount - rec.deposit_amount_payment

    @api.depends('deposit_amount', 'deposit_amount_payment')
    def _compute_payment_state(self):
        """Permet de connaître le statut des paiements de la caution et du transport sur le contrat"""
        for rec in self:
            if rec.deposit_amount_payment == 0:
                rec.payment_state = 'unpaid'
            elif rec.deposit_amount_payment < rec.deposit_amount:
                rec.payment_state = 'partial'
            elif rec.deposit_amount_payment == rec.deposit_amount:
                rec.payment_state = 'paid'

    def button_open_freezer_return(self):
        """Mise en place du box intelligent des Retours Congélateurs et ses données"""
        return {

            'name': 'Retour Congélateur',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'context': {'edit': False, 'create': False},
            'domain': [('freezer_return_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

    @api.depends('freezer_return_ids')
    def _compute_freezer_return_count(self):
        """La fonction permettant de calculer le nombre de rétour Congélateur"""
        for rec in self:
            rec.freezer_return_count = len(rec.freezer_return_ids)

    def button_open_customer_delivery(self):
        """Mise en place du box intelligent des Paiements Cautions Client et ses données"""
        return {

            'name': 'Paiement Caution Client',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'context': {'edit': False, 'create': False},
            'domain': [('paiement_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

    @api.depends('payment_ids')
    def _compute_customer_paiement_count(self):
        """La fonction permettant de calculer le nombre de Paiements Cautions Clients"""
        for rec in self:
            rec.customer_paiement_count = len(rec.payment_ids)


    def action_approval(self):
        """
        in_consultation -> in_progress
        @return:
        """
        for rec in self:
            rec.state = 'approval'

    def action_validate(self):
        """
        in_consultation -> in_progress
        @return:
        """
        for rec in self:
            rec.state = 'in_progress'

    def action_return(self):
        """
        Passe l'état à 'expired' et crée les mouvements de stock nécessaires.
        Cette méthode ne s'exécute que si l'état actuel est 'expired'.
        """
        for rec in self:
            # Vérifier que l'état est 'expired' avant d'exécuter le code
            if rec.state == 'expired':
                raise UserError("L'état est déjà 'expiré'. Cette action ne peut être exécutée qu'une seule fois.")
            # Recherche du type de picking pour un transfert gratuit
            picking_type = self.env['stock.picking.type'].search([('is_free_transfer', '=', True), ('company_id', '=', self.env.company.id)],
                limit=1
            )
            picking_type_return = picking_type.return_picking_type_id
            # Vérifier si le type de picking est trouvé
            if not picking_type_return:
                raise UserError("Aucun type de picking 'transfert gratuit' trouvé pour cette société.")
            # Récupération des emplacements source et destination à partir du type de picking
            location_id = picking_type_return.default_location_src_id
            location_dest_id = picking_type_return.default_location_dest_id
            # Vérifier si les emplacements sont valides
            if not location_id or not location_dest_id:
                raise UserError(
                    "Les emplacements source ou destination n'ont pas été définis pour ce type d'opération.")
            # Vérifier que le numéro de série (lot_id) est sélectionné
            if not rec.lot_id:
                raise UserError("Veuillez sélectionner un numéro de série.")
            # Créer un picking de stock pour la gestion de l'affectation
            picking = self.env['stock.picking'].create({
                'partner_id': rec.customer_id.id,
                'picking_type_id': picking_type_return.id,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'origin': f"{rec.name} - {rec.lot_id.name}",
                'freezer_return_id': rec.id,
            })
            # Créer un mouvement de stock
            stock_move = self.env['stock.move'].create({
                'name': f"Retour congélateur serie {rec.lot_id.name} au client {rec.customer_id.name}",
                'product_id': rec.lot_id.product_id.id,
                'product_uom': rec.lot_id.product_id.uom_id.id,
                'product_uom_qty': 1,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'picking_id': picking.id,
            })
            # Créer la ligne de mouvement de stock
            stock_move_line = self.env['stock.move.line'].create({
                'move_id': stock_move.id,
                'product_id': rec.lot_id.product_id.id,
                'lot_id': rec.lot_id.id,
                'quantity': 1,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
            })
            # Passer l'état à 'expired' une fois que tout est créé
            rec.state = 'expired'
            # Optionnel : Retourner un message de succès ou effectuer des actions supplémentaires
            picking.action_confirm()
            picking.action_assign()

        # Afficher une notification de succès
        return True
    def action_validate(self):
        """
        in_consultation -> in_progress
        @return:
        """
        for rec in self:
            rec.state = 'in_progress'

    def button_open_return_freezer(self):
        return {

            'name': 'Retour Congélateur ',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'context': {'edit': False, 'create': False},
            'domain': [('contract_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

    def action_expired(self):
        """
        in_consultation -> expired
        @return:
        """
        for rec in self:

            rec.date_end = fields.Date.today()  # Date d'expiration du contrat
            rec.action_return()  # Retour du congélateur au client
            rec.state = 'expired'

    def action_cancel(self):
        """
        in_consultation -> cancel
        @return:
        """
        for rec in self:
            rec.state = 'cancel'
    def action_new(self):
        """
        in_consultation -> new
        @return:
        """
        for rec in self:
            rec.state = 'new'
    @api.model
    def create(self, vals):
        # Génération d'une référence unique pour le contract
        vals['name'] = self.env['ir.sequence'].next_by_code('customer.contract')
        return super(CustomerContract, self).create(vals)
    def action_expire_contract(self):
        """Méthode pour gérer le retour en stock lorsqu'un contrat expire."""
        if self.state == 'expired':
            # Récupérer le lot de produit du congélateur
            lot = self.lot_id
            if lot:
                # Effectuer le retour en stock avec la quantité du congélateur
                self._update_product_stock(lot, 1)  # Remise du produit en stock (quantité à ajuster)
                self.state = 'cancel'  # Mettre à jour l'état du contrat si nécessaire
            else:
                raise UserError("Aucun lot de produit associé pour ce contrat.")

    @api.onchange('num_freezer')
    def _onchange_num_freezer(self):
        """
        Remplit freezer_id en fonction du numéro de série sélectionné dans num_freezer.
        """
        for record in self:
            if record.lot_id:
                # Recherche le congélateur correspondant au numéro de série sélectionné
                freezer = self.env['freezer.assignment'].search(
                    [('lot_id', '=', record.lot_id)], limit=1
                )
                record.freezer_id = freezer.id if freezer else False
            else:
                record.freezer_id = False

class Stock(models.Model):
    _inherit = 'stock.picking'

    delivery_id = fields.Many2one(comodel_name='freezer.assignment', string='Livraison', required=False)
    freezer_return_id = fields.Many2one(comodel_name='customer.contract', string='Retour Congélateur', required=False)


class FieldVisit(models.Model):
    _name = 'field.visit'
    _description = 'Visite terrain'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence Visite', required=False, copy=False, readonly=True, default="Nouveau")
    customer_id = fields.Many2one('res.partner', string='Client', required=True,tracking=True)
    customer_number = fields.Char(related='customer_id.ref', string='Téléphone', readonly=True)
    customer_email = fields.Char(related='customer_id.email', string='Email', readonly=True)
    freezer_condition = fields.Selection([('good', 'Bon'),('dirty', 'Sale'),('broken-down', 'En panne'),],string="Etat Congélateur",required=True)
    order = fields.Selection([('yes', 'OUI'),('no', 'NON'),],string="Commande",required=True)
    products_present = fields.Selection([('yes', 'OUI'),('no', 'NON'),],string="Produits présents",required=True)
    dlv = fields.Selection([('yes', 'OUI'),('no', 'NON'),],string="DLV",required=True)
    storage = fields.Selection([('good', 'Bon'),('bad', 'Mauvais'),('means', 'Moyen')],string="Rangement")
    observation = fields.Selection([('Power_cut', "Coupure d'électricité"),('freezer_disconnected', 'Débranchement Congélateur'),('melted_products', 'Produits fondu')],string="Observation")
    note = fields.Html(string="Note")
    date_visit = fields.Datetime(string="Date de Visite",required=True)
    geolocation_position = fields.Float(string="Position Géographique",digits=(16, 5))
    freezer_capacity = fields.Float(string='Capacité du Congélateur', related='lot_id.product_id.capacity',required=False, tracking=True)
    lot_id = fields.Many2one(comodel_name='stock.lot',string='N° de série', required=False,  tracking=True)
    product_id = fields.Many2one('product.product',string='Congélateur', required=False)
    state = fields.Selection([('send', 'Envoyé'),('cancel', 'Annulé'),])
    freezer_id = fields.Many2one(comodel_name='freezer.assignment', string='Reference Affectation', required=False, tracking=True)
    scanned_qr_code = fields.Binary(string="Code QR scanné")
    latitude = fields.Float("Latitude", digits=(10, 6))
    longitude = fields.Float("Longitude", digits=(10, 6))

    @api.model
    def open_field_visit_form(self, **kwargs):
        if not self.scanned_qr_code:
            raise UserError(_("No QR code scanned! Please scan a QR code."))

        # Rechercher le congélateur assigné avec le QR code
        assignment = self.env['freezer.assignment'].search(
            [('lot_id', '=', self.scanned_qr_code)], limit=1
        )

        if not assignment:
            raise UserError(_("No freezer found for the scanned QR code!"))

        # Vérifier si le congélateur est lié au bon client
        if assignment.customer_id != self.env.user.partner_id:
            raise UserError(_("This freezer is not assigned to your customer!"))

        # Créer ou ouvrir le formulaire de visite terrain
        return {
            'type': 'ir.actions.act_window',
            'name': 'Field Visit',
            'res_model': 'field.visit',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'context': self.env.context,
        }

    def action_cancel(self):
        """
        in_consultation -> cancel
        @return:
        """
        for rec in self:
            rec.state = 'cancel'

    def action_send(self):
        """
        in_consultation -> send
        @return:
        """
        for rec in self:
            rec.state = 'send'

    @api.model
    def create(self, vals):
        # Génération d'une référence unique pour le contract
        vals['name'] = self.env['ir.sequence'].next_by_code('field.visit')
        return super(FieldVisit, self).create(vals)


class AccountMove(models.Model):
    _inherit = 'account.payment'

    paiement_id = fields.Many2one(comodel_name='customer.contract', string='Paiement', required=False)


