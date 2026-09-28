# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    finsetter_twilio_account_sid = fields.Char(
        string='Twilio Account SID', config_parameter='finsetter_crm.twilio_account_sid')
    finsetter_twilio_auth_token = fields.Char(
        string='Twilio Auth Token', config_parameter='finsetter_crm.twilio_auth_token')
    finsetter_twilio_whatsapp_from = fields.Char(
        string='Twilio WhatsApp Sender', config_parameter='finsetter_crm.twilio_whatsapp_from',
        help="E.g. whatsapp:+14155238886 (Twilio sandbox number) or your approved "
             "WhatsApp Business sender, in E.164 format.")
    finsetter_twilio_sms_from = fields.Char(
        string='Twilio SMS Sender', config_parameter='finsetter_crm.twilio_sms_from',
        help="Your Twilio SMS-capable phone number, in E.164 format, e.g. +14155551234.")
    finsetter_twilio_voice_from = fields.Char(
        string='Twilio Voice Caller ID', config_parameter='finsetter_crm.twilio_voice_from',
        help='A Twilio number enabled for outbound voice calls, in E.164 format.')
    finsetter_public_webhook_url = fields.Char(
        string='Public CRM URL', config_parameter='finsetter_crm.public_webhook_url',
        help='HTTPS URL reachable by Twilio, without a trailing slash.')
    finsetter_webhook_token = fields.Char(
        string='Webhook Secret Token', config_parameter='finsetter_crm.webhook_token')
