# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class FreezerPaiementWz(models.TransientModel):
    _name = 'freezer.paiement.wz'
    _description = _('FreezerPaiementWz')

    contract_id = fields.Many2one(
        string=_('Contrat Client'),
        comodel_name='customer.contract',
    )
    amount_refund = fields.Monetary(string=_('Remboursement Caution'), default=0.0)
    amount = fields.Monetary(string=_('Montant'))
    is_refund = fields.Boolean(string=_('Paiement de Retour'), default=False)
    currency_id = fields.Many2one("res.currency", string=_('Devise'),default=lambda self: self.env.user.company_id.currency_id)
    date_paiement = fields.Date(string=_('Date de Paiement'),default=fields.Date.today)
    memo = fields.Text(string=_('Memo'))
    journal_id = fields.Many2one('account.journal', string='Journal des paiements', required=False ,domain="[('type','in', ('bank','cash') )]")


    @api.model
    def default_get(self, fields):
        res = super(FreezerPaiementWz, self).default_get(fields) 
        is_refund = self.env.context.get('is_refund', False)
        contract_id = self.env['customer.contract'].browse(self.env.context.get('active_id'))
        if not contract_id:
            raise ValidationError('Veuillez selectionner un contrat client')
        if contract_id.deposit_amount_of == 0 and not is_refund:
            raise ValidationError('La caution a été totalement payé')
        res.update({
            'amount': contract_id.deposit_amount_of,
            'contract_id': contract_id.id,
            'is_refund': is_refund,
            'amount_refund': contract_id.deposit_amount if is_refund else 0.0
        })
        return res
    
    def payment_wz(self,type,amount,type_partner,ref):
        for rec in self:
            payment_driver = self.env['account.payment'].create({
                'partner_id': rec.contract_id.customer_id.id,
                'amount': amount,
                'paiement_id': rec.contract_id.id,
                'payment_type': type,
                'partner_type': type_partner,
                'journal_id': rec.journal_id.id,
                'date': rec.date_paiement,
                'ref': ref
            })
            payment_driver.action_post()
            return True

    def confirm_payment(self):
        for rec in self:
            if rec.amount > rec.contract_id.deposit_amount_of:
                raise ValidationError('Le montant du paiement est supérieur à la caution')
            if rec.contract_id.transport_amount !=0 and not rec.contract_id.is_driver_paid:
                ref = f"Paiement Transport Congélateur - {rec.memo}"
                rec.payment_wz('inbound', rec.contract_id.transport_amount, 'customer', ref)
                rec.contract_id.is_driver_paid = True
            if rec.is_refund:
                ref = f"Remboursement de la caution du client {rec.contract_id.customer_id.name}  - {rec.memo}"
                rec.payment_wz('outbound', rec.amount_refund, 'supplier', ref)
                rec.contract_id.state = 'done'
            else :
                ref = f"Paiement de la caution  - {rec.memo}"
                rec.payment_wz('inbound', rec.amount, 'customer', ref)
                rec.contract_id.deposit_amount_payment = rec.contract_id.deposit_amount_payment + rec.amount
            
            return {'type': 'ir.actions.act_window_close'}
