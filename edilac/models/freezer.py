# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class Product(models.Model):
    _inherit = 'product.product'

    capacity = fields.Float(string='Capacité du congélateur', required=False, help="Une fois coché, le produit sera marqué comme un congélateur")
    freezer = fields.Boolean(string='Marqué Comme un Congélateur', related="product_tmpl_id.freezer",store=True)

