# -*- coding: utf-8 -*-
# from odoo import http


# class Edilacte(http.Controller):
#     @http.route('/edilacte/edilacte', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/edilacte/edilacte/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('edilacte.listing', {
#             'root': '/edilacte/edilacte',
#             'objects': http.request.env['edilacte.edilacte'].search([]),
#         })

#     @http.route('/edilacte/edilacte/objects/<model("edilacte.edilacte"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('edilacte.object', {
#             'object': obj
#         })
