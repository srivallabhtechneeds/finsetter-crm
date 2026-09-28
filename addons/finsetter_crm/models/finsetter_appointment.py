# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class FinsetterAppointment(models.Model):
    """Spec section 6: Appointment booking with real Google Calendar sync.

    Rather than hand-roll Google OAuth, this model creates/owns a standard
    `calendar.event`. Odoo's own (Community/LGPL-3) `google_calendar`
    module then syncs that event to Google automatically once the advisor
    connects their Google account (Settings > General Settings >
    Integrations, after installing the "Google Calendar" app and entering a
    Google OAuth Client ID/Secret) — so the sync is real, but the OAuth risk
    sits entirely on Odoo's own already-shipped, tested integration rather
    than new code here. See README for the exact setup steps.
    """
    _name = 'finsetter.appointment'
    _description = 'Finsetter Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'appointment_datetime'

    name = fields.Char(compute='_compute_name', store=True)

    lead_id = fields.Many2one('crm.lead', string='Lead / Opportunity', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    advisor_id = fields.Many2one('res.users', string='Advisor', default=lambda self: self.env.user, tracking=True)
    product_line_id = fields.Many2one('finsetter.policy.product.line', string='Product Line')

    appointment_datetime = fields.Datetime(required=True, tracking=True)
    duration = fields.Float(default=0.5, help="Hours. Matches the site's free 30-45 minute consultation.")
    mode = fields.Selection([
        ('virtual', 'Virtual'),
        ('in_person', 'In Person'),
        ('phone', 'Phone'),
    ], default='virtual', required=True)

    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ], default='scheduled', required=True, tracking=True)

    calendar_event_id = fields.Many2one('calendar.event', string='Calendar Event', readonly=True, ondelete='set null')
    reminder_sent = fields.Boolean(default=False)
    notes = fields.Text()

    @api.depends('partner_id', 'appointment_datetime')
    def _compute_name(self):
        for rec in self:
            when = fields.Datetime.to_string(rec.appointment_datetime) if rec.appointment_datetime else ''
            rec.name = '%s - %s' % (rec.partner_id.name or 'Appointment', when)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._sync_calendar_event()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('appointment_datetime', 'duration', 'partner_id', 'advisor_id', 'status', 'mode')):
            for rec in self:
                rec._sync_calendar_event()
        return res

    def _sync_calendar_event(self):
        """Create/update the linked calendar.event so the appointment shows
        on the advisor's Odoo calendar and, once Google sync is configured,
        their Google Calendar too."""
        Event = self.env['calendar.event']
        for rec in self:
            if rec.status == 'cancelled':
                if rec.calendar_event_id:
                    rec.calendar_event_id.write({'active': False})
                continue
            if not rec.appointment_datetime:
                continue
            partner_ids = [rec.advisor_id.partner_id.id]
            if rec.partner_id:
                partner_ids.append(rec.partner_id.id)
            vals = {
                'name': 'Finsetter: %s' % (rec.name or rec.partner_id.name or 'Appointment'),
                'start': rec.appointment_datetime,
                'stop': rec.appointment_datetime + timedelta(hours=rec.duration or 0.5),
                'duration': rec.duration or 0.5,
                'partner_ids': [(6, 0, list(set(partner_ids)))],
                'user_id': rec.advisor_id.id,
                'description': rec.notes or '',
                'location': 'Virtual (Finsetter CRM)' if rec.mode == 'virtual' else (rec.mode or ''),
            }
            if rec.calendar_event_id:
                rec.calendar_event_id.write(vals)
            else:
                rec.calendar_event_id = Event.create(vals)

    def action_mark_confirmed(self):
        self.write({'status': 'confirmed'})

    def action_mark_completed(self):
        self.write({'status': 'completed'})

    def action_mark_no_show(self):
        self.write({'status': 'no_show'})

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_open_calendar_event(self):
        self.ensure_one()
        if not self.calendar_event_id:
            return False
        return {
            'name': 'Calendar Event',
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'res_id': self.calendar_event_id.id,
        }

    @api.model
    def _cron_send_reminders(self):
        """Remind customers of upcoming appointments (next 24h) once, by
        raising a high-priority follow-up activity for the advisor. Called
        by ir_cron_data.xml."""
        window_start = fields.Datetime.now()
        window_end = window_start + timedelta(hours=24)
        upcoming = self.search([
            ('status', 'in', ('scheduled', 'confirmed')),
            ('reminder_sent', '=', False),
            ('appointment_datetime', '>=', window_start),
            ('appointment_datetime', '<=', window_end),
        ])
        for appt in upcoming:
            appt.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='Appointment reminder due',
                note="Remind %s about their appointment on %s." % (
                    appt.partner_id.name, appt.appointment_datetime),
                user_id=appt.advisor_id.id or self.env.uid,
            )
            appt.reminder_sent = True
