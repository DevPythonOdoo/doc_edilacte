from odoo import fields, models, api


class FieldVisitWizard(models.TransientModel):
    _name = 'field.visit.wizard'
    _description = 'Wizard pour Visite Terrain'

    # Champs similaires à FieldVisit
    customer_id = fields.Many2one('res.partner', string='Client', required=True)
    customer_number = fields.Char(related='customer_id.ref', string='Téléphone', readonly=True)
    customer_email = fields.Char(related='customer_id.email', string='Email', readonly=True)
    freezer_condition = fields.Selection([('good', 'Bon'),('dirty', 'Sale'),('broken-down', 'En panne'), ], string="État Congélateur", required=True)
    order = fields.Selection([('yes', 'OUI'),('no', 'NON'),], string="Commande", required=True)
    products_present = fields.Selection([('yes', 'OUI'),('no', 'NON'),], string="Produits présents", required=True)
    dlv = fields.Selection([('yes', 'OUI'),('no', 'NON'),], string="DLV", required=True)
    storage = fields.Selection([('good', 'Bon'),('bad', 'Mauvais'),('means', 'Moyen'),], string="Rangement")
    observation = fields.Selection([('Power_cut', "Coupure d'électricité"),('freezer_disconnected', 'Débranchement Congélateur'),('melted_products', 'Produits fondus'),], string="Observation")
    note = fields.Html(string="Note")
    date_visit = fields.Datetime(string="Date de Visite", required=True, default=fields.Datetime.now)
    geolocation_position = fields.Float(string="Position Géographique", digits=(16, 5))
    freezer_id = fields.Many2one('freezer.assignment', string='Référence Affectation', required=False)
    lot_id = fields.Many2one('stock.lot', string='N° de série', required=False)
    freezer_capacity = fields.Float(string='Capacité du Congélateur', related='lot_id.product_id.capacity',required=False, tracking=True)
    product_id = fields.Many2one('product.product', string='Congélateur', required=False)
    state = fields.Selection([('send', 'Envoyé'), ('cancel', 'Annulé'), ])
    scanned_qr_code = fields.Char(string="QR Code Scanné", readonly=True)

    def action_create_field_visit(self):
        """Créer une visite terrain depuis les données du wizard"""
        self.ensure_one()  # Un seul record à la fois
        visit_vals = {
            'customer_id': self.customer_id.id,
            'customer_number': self.customer_number.id,
            'customer_email': self.customer_email.id,
            'freezer_condition': self.freezer_condition,
            'order': self.order,
            'products_present': self.products_present,
            'dlv': self.dlv,
            'storage': self.storage,
            'observation': self.observation,
            'note': self.note,
            'date_visit': self.date_visit,
            'geolocation_position': self.geolocation_position,
            'freezer_id': self.freezer_id.id,
            'lot_id': self.lot_id.id,
            'product_id': self.product_id.id,
            'freezer_capacity': self.freezer_capacity.id,
            'state': self.state,
        }
        # Créer l'enregistrement dans FieldVisit
        self.env['field.visit'].create(visit_vals)
