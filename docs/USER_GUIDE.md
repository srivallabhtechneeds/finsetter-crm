# Finsetter CRM User Guide

This guide describes the Finsetter CRM Odoo 17 application, its daily workflows, configuration, and operational limits. The CRM is an Odoo addon served locally through Docker Compose with PostgreSQL.

## Contents

- [Start the CRM](#start-the-crm)
- [Navigation](#navigation)
- [New Leads](#new-leads)
- [Existing Leads](#existing-leads)
- [Follow-ups](#follow-ups)
- [Other CRM areas](#other-crm-areas)
- [Users and access](#users-and-access)
- [Configuration](#configuration)
- [Operations and maintenance](#operations-and-maintenance)
- [Production checklist and limitations](#production-checklist-and-limitations)

## Start the CRM

### Requirements

- Docker Desktop with its Linux engine enabled, or Docker Engine and Docker Compose.
- Network access to Docker Hub the first time the Odoo and PostgreSQL images are downloaded.
- A browser. The default local URL is `http://localhost:8069`.

### Windows

Run `Start-FinsetterCRM.bat` from the project folder. It builds and starts the services, waits for Odoo, then opens the browser. The first installation can take several minutes.

### macOS, Linux, or WSL

From the project folder:

```bash
./scripts/up.sh
```

Equivalent Compose command:

```bash
docker compose up -d --build
```

Wait for `Modules loaded.` in the Odoo logs, then open `http://localhost:8069`. A new installation uses the documented Odoo bootstrap login `admin` / `admin`; change the password immediately. The database and administrator passwords must be changed before any real deployment.

Demo records are disabled by default. Enabling demo data after a database has already been created requires a fresh database; `docker compose down -v` deletes the database volume and all stored CRM data, so use that only when a full reset is intended.

## Navigation

The app switcher opens **Finsetter CRM**. Main areas:

| Area | Contents |
|---|---|
| Dashboard | Pipeline totals, renewals, consent gaps, SLA, calls, and team metrics |
| Sales | Pipeline, New Leads, Existing Leads, Product Matches, Appointments, Follow-ups |
| Customers | Policies, Claims, Call Logs, Consent Register, Documents & KYC |
| Marketing | Campaigns and Client Testimonials |
| Tools | Financial Calculators |
| Reporting | Pipeline, policy/renewal, campaign, and claims analysis |
| Configuration | Product lines, Financial Products, Follow-up Templates, and integration settings |

## New Leads

**Sales → New Leads** is for unqualified prospects that do not yet have a policy. It uses Odoo's standard list/form workflow, including list search, filters, grouping, and CSV import/export controls.

The list includes the CRM lead name, phone, email, source, interested product line, assigned agent, and Finsetter Lead Status. Optional columns can be enabled from the list-view column selector.

### Lead statuses

- **New**: captured but not yet contacted.
- **Contacted**: first contact has been made.
- **Interested**: the prospect is considering a product.
- **Quote Sent**: a quote has been shared.
- **Converted**: converted to a customer or policy.
- **Lost**: the prospect did not proceed.

Lead Status is a Finsetter qualification field. Odoo's pipeline **Stage** is a separate field; changing one does not automatically change the other.

### Create or import leads

Use **New** to open the lead form. Enter a name and the available contact information, source, product line, and agent. The form includes the normal Odoo lead notes and chatter, which provide the activity timeline. It also includes:

- Preferred contact channels: WhatsApp, SMS, Email Channel, and AI Call preference.
- Call consent and preferred language.
- Health Condition: Not Assessed, Healthy, or Unhealthy. Health Problem is shown and required when Unhealthy is selected.
- Customer profile, financial goals, requirements, and consultation mode.
- Service page and product-line talking points when configured.

To import, open the lead list and use Odoo's **Import records** control. Prepare a CSV with headers matching Odoo field labels or technical field names. Common columns are `name`, `phone`, `email_from`, `source_id`, `product_line_id`, `user_id`, and `lead_status`. Many2one values such as source, product line, and agent must match existing records. Test an import with a small file first and review Odoo's field mapping before confirming.

New Leads excludes leads linked to a policy and defaults newly created records to New Prospect. Once a policy is recorded against a lead, it is treated as a policyholder workflow.

## Existing Leads

**Sales → Existing Leads** is the policyholder list. Each row represents a `finsetter.policy` record, not a separate customer record. The list displays customer, policy number, policy type, premium, renewal due date, and policy status. Due dates are highlighted as they approach.

Use the policy form to complete these actions:

### Schedule a meeting or call

Choose **Schedule Meeting / Call**, select the appointment time, mode, and advisor, and save. Appointments create linked Odoo calendar events. Booking a meeting stops pending automated renewal follow-ups for the customer's active policy or the linked policy.

### Compare an upgrade

Choose **Compare Upgrade Plans**. The CRM runs its transparent product matching rules and opens the comparison list. It shows the current policy and premium beside the recommended products, match score, and rationale. If an older policy has no originating CRM lead, the action creates and links an upgrade-review lead first.

### Renew a policy

The policy list's **Renew** action advances the renewal date using the product line's renewal cycle and returns the policy to Active. The policy form also has **Mark Renewed**. Renewal Quote and Payment Link are editable policy fields; enter the real quote and secure payment URL supplied by your insurer/payment provider. This CRM does not calculate insurer premiums or generate payment links itself.

**Send Renewal Quote** creates and sends the renewal email using the active renewal email template. It requires an outgoing mail server, a customer email address, and populated quote/payment fields. A successful provider send is recorded in Follow-ups.

The policy's automatic state values include Active, Renewal Due, Lapsed, Renewed, and Cancelled. The existing-policy list highlights the main Active, Renewal Due, and Lapsed states.

## Follow-ups

**Sales → Follow-ups** is the searchable message history. **Configuration → Follow-up Templates** is where CRM Administrators can edit the default templates.

Templates are provided for each of these purposes and channels:

| Purpose | Channels |
|---|---|
| Meeting / Call Scheduling | Email, SMS, WhatsApp, Automated Voice Call (TTS) |
| Policy Upgrade | Email, SMS, WhatsApp, Automated Voice Call (TTS) |
| Policy Renewal | Email, SMS, WhatsApp, Automated Voice Call (TTS) |

Supported template variables include `{customer_name}`, `{policy_number}`, `{renewal_date}`, `{premium}`, `{payment_link}`, `{lead_name}`, and `{company_name}`. Unavailable values render as blank.

### Automatic renewal sequence

A daily cron checks each active policy and creates one reminder for each matching date in a renewal cycle:

| Days before renewal | Channel |
|---:|---|
| 30 | Email |
| 15 | SMS |
| 7 | WhatsApp |
| 1 | Automated Voice Call (Twilio text-to-speech) |

A separate dispatcher checks every 15 minutes for manually queued messages whose scheduled time has arrived. Each message has a log record with status, provider reference, error detail, sent time, and reply time.

For Twilio SMS/WhatsApp and voice, status callbacks can update Sent, Delivered, Read, and Failed states when the channel/provider reports them. Incoming Twilio SMS/WhatsApp replies can mark the matching customer follow-up Replied. Odoo incoming mail threading can mark email replies when mail-server and catchall routing are configured.

A reply, booking an appointment, or renewing the policy stops the current renewal sequence. Queued messages are marked Cancelled. New renewal dates begin a new policy cycle.

## Other CRM areas

- **Pipeline**: opportunities, stages, forecast, and standard Odoo CRM activity views.
- **Product Matches**: product recommendations and decision/conversion status.
- **Appointments**: calendar, advisor, customer, consultation mode, and appointment status.
- **Policies**: all policy records, renewal scanning, claims, consent, and payment details.
- **Call Logs**: structured inbound/outbound calls, consent confirmation, outcomes, notes, and advisor follow-up activities.
- **Consent Register**: customer consent records by purpose and communication channel. Capture appropriate consent before contacting customers.
- **Claims**: track claims from submission through settlement.
- **Documents & KYC**: document upload and Pending/Verified/Rejected review.
- **Campaigns**: build a recipient list and send WhatsApp/SMS through Twilio or email through Odoo mail. Campaign sends are distinct from the renewal follow-up sequence.
- **Financial Products**: product catalogue, eligibility, ranges, tenure, benefits, and commission. Demo product terms are illustrative and must be replaced with approved real terms.
- **Financial Calculators**: estimates for insurance, investment, tax, retirement, loans, and compound interest.
- **Customer Portal**: portal users can view only their own policies, appointments, documents, and claims at `/my`.

## Users and access

| Role | Intended access |
|---|---|
| CRM Administrator | Full configuration and CRM access |
| Manager | Company-wide management and reporting |
| Team Lead | Team-level oversight and advisor permissions |
| Financial Advisor | Assigned leads, policies, calls, follow-ups, and related customer workflows |
| Sales Executive | Lead capture, qualification, appointments, and campaign work; read-oriented policy access |
| Compliance Officer | Compliance/audit-oriented read access |
| Customer (portal) | Own portal records only |

Assign groups under **Settings → Users & Companies → Users → Other Rights → Finsetter CRM**. Review the installed security groups and record rules before changing access for production users.

## Configuration

### Email

Configure an outgoing mail server in Odoo's General Settings before sending email follow-ups or quotes. For automatic email reply detection, also configure an incoming mail server and Odoo's catchall/threading so replies attach to the original follow-up thread. Standard SMTP alone does not provide read receipts.

### Twilio messaging and voice

Under **Settings → General Settings → Finsetter CRM**, configure the Account SID, Auth Token, SMS sender, WhatsApp sender, Voice-capable caller ID, public CRM URL, and webhook secret as applicable. The SMS/WhatsApp/voice numbers must be provisioned for the chosen Twilio products.

The CRM attaches outbound status callback URLs using the public URL and secret. In Twilio, set the inbound messaging webhook to:

```text
https://<public-crm-host>/finsetter/twilio/inbound?token=<webhook-secret>
```

Use HTTP POST. The webhook host must be reachable from Twilio over HTTPS; `localhost` is not publicly reachable. Keep the webhook secret private and rotate it if exposed.

### Calendar

Each appointment creates an Odoo `calendar.event`. Install/configure Odoo's Google Calendar integration and have each advisor connect their account if Google Calendar synchronization is required.

## Operations and maintenance

Run commands from the repository root.

| Task | Windows | macOS/Linux/WSL |
|---|---|---|
| Start | `Start-FinsetterCRM.bat` | `./scripts/up.sh` |
| Stop, keep data | `Stop-FinsetterCRM.bat` | `./scripts/down.sh` |
| View logs | `View-Logs.bat` | `./scripts/logs.sh` |
| Upgrade addon, keep data | `Upgrade-Module.bat` | `./scripts/upgrade_module.sh` |
| Static validation | `scripts\validate.sh` via Git Bash | `./scripts/validate.sh` |

Do not run `docker compose down -v` unless you intend to delete the PostgreSQL data volume. Back up the database and Odoo filestore before upgrades or production maintenance. To inspect startup errors, use `docker compose logs --tail 200 odoo` and `docker compose ps`.

The static validator checks XML well-formedness, Python syntax, and manifest keys. A successful static check does not replace an Odoo database upgrade or provider delivery test.

## Production checklist and limitations

- Replace default database and Odoo administrator passwords; use strong, unique secrets.
- Use HTTPS, a public domain, and a protected webhook token for Twilio callbacks.
- Configure and test SMTP, incoming mail routing, Twilio SMS/WhatsApp senders, and voice caller ID before enabling customer contact automation.
- Verify consent, contact details, approved message content, quiet hours, and local insurance/privacy regulations before sending.
- Replace illustrative financial product terms; confirm renewal amounts and payment links with the insurer/payment provider.
- The voice channel is Twilio `<Say>` text-to-speech, not a conversational AI voice agent. A separate AI voice service and integration are required for AI conversations.
- Delivery/read receipts depend on provider and channel capabilities. Email read receipts are not supplied by ordinary SMTP.
- Renewal quotes and payment URLs are stored/displayed by the CRM; the CRM does not underwrite policies, calculate insurer quotes, or process payments.
- External messaging was not exercised without customer-owned provider credentials. Use test numbers and test mailboxes before a production rollout.
