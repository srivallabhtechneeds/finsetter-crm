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
