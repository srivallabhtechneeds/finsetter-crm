# -*- coding: utf-8 -*-
import hmac
import re

from odoo import http
from odoo.http import request


class FinsetterTwilioWebhooks(http.Controller):
    def _authorized(self):
        expected = request.env['ir.config_parameter'].sudo().get_param('finsetter_crm.webhook_token') or ''
        supplied = request.httprequest.args.get('token', '')
        return bool(expected) and hmac.compare_digest(expected, supplied)

    @http.route('/finsetter/twilio/status', type='http', auth='public', methods=['POST'],
                csrf=False, save_session=False)
    def twilio_status(self, **kwargs):
        if not self._authorized():
            return request.make_response('Forbidden', status=403)
        params = request.httprequest.values
        reference = params.get('MessageSid') or params.get('CallSid')
        provider_status = params.get('MessageStatus') or params.get('CallStatus') or ''
        if reference:
            log = request.env['finsetter.followup.log'].sudo().search(
                [('provider_reference', '=', reference)], limit=1)
            if log:
                log._apply_provider_status(provider_status)
        return request.make_response('', status=204)

    @http.route('/finsetter/twilio/inbound', type='http', auth='public', methods=['POST'],
                csrf=False, save_session=False)
    def twilio_inbound(self, **kwargs):
        if not self._authorized():
            return request.make_response('Forbidden', status=403)
        sender = request.httprequest.values.get('From', '')
        digits = re.sub(r'\D', '', sender)
        logs = request.env['finsetter.followup.log'].sudo().search([
            ('status', 'in', ('sent', 'delivered', 'read')),
            ('partner_id', '!=', False),
        ], order='sent_at desc, id desc', limit=250)
        for log in logs:
            partner = log.partner_id
            stored_numbers = [re.sub(r'\D', '', number or '') for number in (partner.mobile, partner.phone)]
            if digits and any(number and (number.endswith(digits) or digits.endswith(number))
                              for number in stored_numbers):
                log.action_mark_replied()
                break
        response = '<Response><Message>Thanks, your response has been recorded.</Message></Response>'
        return request.make_response(response, headers=[('Content-Type', 'text/xml; charset=utf-8')])