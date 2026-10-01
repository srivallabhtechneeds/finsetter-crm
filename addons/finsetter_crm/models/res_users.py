# -*- coding: utf-8 -*-
from email.utils import formataddr

from odoo import api, fields, models

CHANNEL_ADMIN_GROUPS = 'base.group_system,finsetter_crm.group_finsetter_manager'

CHANNEL_LABELS = {
    'email': 'Email',
    'whatsapp': 'WhatsApp',
    'sms': 'SMS',
    'voice': 'Voice',
}


class ResUsers(models.Model):
    """Per-user communication channels.

    Each user can send from their own email address / SMS sender / WhatsApp
    number / voice line. A blank channel falls back to the company's shared
    details (Settings > General Settings > Finsetter CRM); a channel that is
    switched off blocks that user from sending on it entirely — it does not
    fall back to the company account. Only administrators and Finsetter
    managers can see or edit any of this.
    """
    _inherit = 'res.users'

    # --- Email ------------------------------------------------------------
    fs_email_enabled = fields.Boolean(
        string='Email Enabled', default=True, groups=CHANNEL_ADMIN_GROUPS)
    fs_email_from = fields.Char(
        string='From Address', groups=CHANNEL_ADMIN_GROUPS,
        help="Address this user's customers receive email from and reply to. "
             "Leave blank to use the company email.")
    fs_mail_server_id = fields.Many2one(
        'ir.mail_server', string='Finsetter Outgoing Mail Server', groups=CHANNEL_ADMIN_GROUPS,
        help="SMTP server used for this user's email (e.g. Brevo). "
             "Leave blank to use Odoo's default outgoing server.")

    # --- SMS --------------------------------------------------------------
    fs_sms_enabled = fields.Boolean(
        string='SMS Enabled', default=True, groups=CHANNEL_ADMIN_GROUPS)
    fs_sms_sender = fields.Char(
        string='SMS Sender', groups=CHANNEL_ADMIN_GROUPS,
        help="Twilio SMS-capable number (E.164, e.g. +14155551234) or approved "
             "alphanumeric sender ID. Leave blank to use the company sender.")

    # --- WhatsApp ---------------------------------------------------------
    fs_whatsapp_enabled = fields.Boolean(
        string='WhatsApp Enabled', default=True, groups=CHANNEL_ADMIN_GROUPS)
    fs_whatsapp_number = fields.Char(
        string='WhatsApp Number', groups=CHANNEL_ADMIN_GROUPS,
        help="WhatsApp Business number in E.164 format, e.g. +919490374717. "
             "Leave blank to use the company WhatsApp sender.")
    fs_whatsapp_meta_phone_id = fields.Char(
        string='Meta Phone Number ID', groups=CHANNEL_ADMIN_GROUPS,
        help="Phone Number ID of this WhatsApp number in Meta Business Manager "
             "(WhatsApp Cloud API).")

    # --- Voice ------------------------------------------------------------
    fs_voice_enabled = fields.Boolean(
        string='Voice Enabled', default=True, groups=CHANNEL_ADMIN_GROUPS)
    fs_voice_phone_number_id = fields.Char(
        string='Phone Number ID', groups=CHANNEL_ADMIN_GROUPS,
        help="ID of the phone number this user's AI voice calls are placed from, "
             "as shown in the voice provider's dashboard.")
    fs_voice_assistant_id = fields.Char(
        string='Assistant ID', groups=CHANNEL_ADMIN_GROUPS,
        help="ID of the voice assistant that handles this user's calls.")
    fs_voice_api_key = fields.Char(
        string='Voice API Key', groups=CHANNEL_ADMIN_GROUPS,
        help="API key for the voice provider account.")

    # --- Administrator ----------------------------------------------------
    fs_channels_active = fields.Boolean(
        string='Channels Active', default=True, groups=CHANNEL_ADMIN_GROUPS,
        help="Master switch. Untick to stop this user sending on every channel.")
    fs_house_identity = fields.Boolean(
        string='House Identity', default=True, groups=CHANNEL_ADMIN_GROUPS,
        help="Present outgoing messages under the company name instead of the "
             "user's own name (e.g. 'Finsetter <leads@…>' rather than 'Ravi <leads@…>').")
    fs_personalised_channels = fields.Char(
        string='Personalised', compute='_compute_fs_personalised_channels',
        groups=CHANNEL_ADMIN_GROUPS,
        help="Channels where this user has their own details instead of the company's.")

    @api.depends('fs_email_from', 'fs_mail_server_id', 'fs_sms_sender', 'fs_whatsapp_number',
                 'fs_whatsapp_meta_phone_id', 'fs_voice_phone_number_id', 'fs_voice_assistant_id')
    def _compute_fs_personalised_channels(self):
        for user in self:
            personal = [
                label for channel, label in CHANNEL_LABELS.items()
                if user._fs_has_personal_details(channel)
            ]
            user.fs_personalised_channels = ', '.join(personal) or 'None — using company details'

    def _fs_has_personal_details(self, channel):
        self.ensure_one()
        user = self.sudo()
        return bool({
            'email': user.fs_email_from or user.fs_mail_server_id,
            'whatsapp': user.fs_whatsapp_number or user.fs_whatsapp_meta_phone_id,
            'sms': user.fs_sms_sender,
            'voice': user.fs_voice_phone_number_id or user.fs_voice_assistant_id,
        }.get(channel))

    # --- Helpers used by the sending code ---------------------------------

    def _fs_channel_block_reason(self, channel):
        """Return why this user may not send on `channel`, or False if allowed."""
        self.ensure_one()
        user = self.sudo()
        label = CHANNEL_LABELS.get(channel, channel)
        if not user.fs_channels_active:
            return "Communication channels are switched off for %s." % user.name
        if not user['fs_%s_enabled' % channel]:
            return "%s is switched off for %s." % (label, user.name)
        return False

    def _fs_email_values(self):
        """`email_from` / `mail_server_id` for an email sent on behalf of this user."""
        self.ensure_one()
        user = self.sudo()
        company = user.company_id
        address = user.fs_email_from or company.email or user.email or ''
        if address and '<' not in address:
            display = company.name if user.fs_house_identity else user.name
            address = formataddr((display, address))
        return {
            'email_from': address,
            'mail_server_id': user.fs_mail_server_id.id or False,
        }

    def _fs_message_senders(self):
        """Personal Twilio senders overriding the company ones (blank = no override)."""
        self.ensure_one()
        user = self.sudo()
        return {
            'sms_from': user.fs_sms_sender or False,
            'whatsapp_from': user.fs_whatsapp_number or False,
        }
