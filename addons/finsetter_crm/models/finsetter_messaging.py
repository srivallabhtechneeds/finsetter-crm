# -*- coding: utf-8 -*-
import logging

import requests
from requests.auth import HTTPBasicAuth

from odoo import models

_logger = logging.getLogger(__name__)

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


class FinsetterMessagingMixin(models.AbstractModel):
    """Shared Twilio REST wiring for real WhatsApp/SMS sends.

    Finsetter uses Twilio as its messaging gateway — Account SID, Auth
    Token and sender numbers are configured once in Settings > General
    Settings > Finsetter CRM (see res_config_settings.py). Any model that
    needs to actually send a WhatsApp/SMS message inherits this mixin and
    calls `_finsetter_send_message`.

    This calls Twilio's real REST Message resource
    (https://www.twilio.com/docs/messaging/api/message-resource) directly
    over HTTPS with Basic Auth — no SDK dependency, just `requests`.
    """
    _name = 'finsetter.messaging.mixin'
    _description = 'Finsetter Messaging (Twilio) Mixin'

    def _finsetter_twilio_config(self):
        icp = self.env['ir.config_parameter'].sudo()
        return {
            'account_sid': icp.get_param('finsetter_crm.twilio_account_sid'),
            'auth_token': icp.get_param('finsetter_crm.twilio_auth_token'),
            'whatsapp_from': icp.get_param('finsetter_crm.twilio_whatsapp_from'),
            'sms_from': icp.get_param('finsetter_crm.twilio_sms_from'),
        }

    def _finsetter_send_message(self, to_number, body, channel='sms'):
        """Send a WhatsApp or SMS message via Twilio. Returns (ok, info_str).

        Never raises — a messaging failure must not block the caller (a
        campaign send loop, a reminder cron); the error is logged and
        handed back for the caller to record on its own record.
        """
        cfg = self._finsetter_twilio_config()
        if not cfg['account_sid'] or not cfg['auth_token']:
            return False, "Twilio is not configured (Settings > General Settings > Finsetter CRM)."
        if not to_number:
            return False, "No destination number on file."

        to_number = to_number.strip()
        if channel == 'whatsapp':
            sender = cfg['whatsapp_from']
            if not sender:
                return False, "No Twilio WhatsApp sender configured."
            from_addr = sender if sender.startswith('whatsapp:') else 'whatsapp:%s' % sender
            to_addr = to_number if to_number.startswith('whatsapp:') else 'whatsapp:%s' % to_number
        else:
            sender = cfg['sms_from']
            if not sender:
                return False, "No Twilio SMS sender configured."
            from_addr, to_addr = sender, to_number

        url = "%s/Accounts/%s/Messages.json" % (TWILIO_API_BASE, cfg['account_sid'])
        try:
            resp = requests.post(
                url,
                data={'From': from_addr, 'To': to_addr, 'Body': body},
                auth=HTTPBasicAuth(cfg['account_sid'], cfg['auth_token']),
                timeout=15,
            )
            payload = resp.json() if resp.content else {}
            if resp.status_code in (200, 201):
                return True, payload.get('sid', 'sent')
            error_msg = payload.get('message') or resp.text
            _logger.warning("Finsetter CRM: Twilio send failed (%s): %s", resp.status_code, error_msg)
            return False, error_msg
        except requests.RequestException as exc:
            _logger.warning("Finsetter CRM: Twilio request error: %s", exc)
            return False, str(exc)
