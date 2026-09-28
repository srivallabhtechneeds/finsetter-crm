# Finsetter CRM

A purpose-built Odoo 17 CRM for **Finsetter Financial Services Pvt. Ltd.**
("Your Money. Simplified." — SEBI Reg. E667968 · IRDAI Lic. 5854206),
built on top of Odoo's Sales/CRM app and packaged as a Docker Compose stack.

For task-by-task instructions, setup, roles, automation, and troubleshooting,
see the [Finsetter CRM User Guide](docs/USER_GUIDE.md).

Content (services, product lines, branding, compliance numbers) was sourced
from [thefinsetter.com](https://www.thefinsetter.com/index.html).

## What you get

- **Lead capture & round-robin assignment** by product line (Health, Life,
  Motor, Home, Travel, NRI, Will Writing, Financial Planning) across four
  dedicated sales teams.
- **New Leads / Existing Leads workspace** — separate prospect and policyholder
  lists. Prospect lists include source, product line, agent, contact details,
  CSV import, and qualification status; policyholder lists include premium,
  renewal date, policy status, meeting, upgrade-comparison, and renewal actions.
- **Lead profile and communication preferences** — notes/activity timeline,
  health condition and conditional health problem, consent, and preferred
  WhatsApp/SMS/email/voice channel flags.
- **Custom pipeline stages** mapped to Finsetter's own process: *Learn → Plan
  → Proposal Shared → KYC & Consent Pending → Grow (Policy Issued)*.
- **Policy & renewal tracking** (`finsetter.policy`): insurer, sum insured,
  premium, renewal quote, payment link, renewal date, meetings, claims, and
  upgrade comparisons.
- **Consent register** (`finsetter.consent`): auditable call/WhatsApp/email/
  data-processing/marketing consent per customer, for SEBI/IRDAI-style
  compliance.
- **Structured call logging** (`finsetter.call.log`) replacing ad-hoc notes,
  with automatic follow-up activities.
- **Automation pipeline**: lead auto-assignment (every 15 min), renewal
  scanning (daily), a KYC-stage consent nudge, and a "record the policy" nudge
  when a deal is won — all via `ir.cron` + `base.automation`, all chatter/
  activity-logged.
- **Finsetter Dashboard** — a modern single-screen OWL dashboard: open
  pipeline value, won-this-month, renewals due, consent gaps, calls today,
  a renewals-due table with one-click "Mark Renewed", pipeline-by-product-line,
  an advisor leaderboard, and a rotating real client testimonial.
- **Client Testimonials** (`finsetter.testimonial`) — the 10 real client
  quotes published on thefinsetter.com, tagged by product line, so advisors
  have proof-points on hand during calls (Marketing menu).
- **Product Line reference data** — each of the 8 product lines now carries
  its real service-page URL and a ready-to-quote talking point (e.g. "₹1
  crore term cover for under ₹1,000/month"), both scraped from the live
  site and surfaced directly on the lead form for one-click sharing.
- **4-hour first-response SLA pipeline** — Finsetter publishes "response
  target: within 4 business hours" on their contact page. Every new lead
  gets a `sla_deadline` computed against a real **Finsetter Business Hours**
  calendar (Mon–Fri 9am–7pm, Sat 10am–4pm, Sun closed — from
  thefinsetter.com/contact.html), auto-marked "Met" the moment a call is
  logged, or escalated to "Breached" (red ribbon on the lead + a
  high-priority activity) by a cron that checks every 30 minutes. Tracked
  live on the Dashboard.
- **Consultation Mode** field (Virtual / In Person / Phone) on every lead,
  matching the free 30–45 minute initial consultation offered on the site.
- Company record now carries Finsetter's real registered office (Plot 245,
  Part Road No. 6, Meenakshi Estates Colony, Hyderabad, Telangana 500067)
  and branding; optional demo data (customers, leads, policies, calls,
  consent records) to see it populated immediately.

### Financial Products, Matching & Campaigns

- **Financial Product catalog** (`finsetter.financial.product`) — 13
  categories in total: the original 8 real Finsetter services plus 5 new
  lines added at your request (Investment Plans/Mutual Funds, Tax-Saving
  Products, Retirement/Pension Plans, Estate Planning, Family Financial
  Planning). Each product carries provider, eligibility, amount range,
  tenure, benefits, required documents, commission and status. Demo data
  ships one or two illustrative products per category — **replace these
  with Finsetter's real product terms before go-live** (Configuration →
  Financial Products).
- **Lead ↔ Product Matching** (`finsetter.lead.product.match`) — a
  transparent, rules-based recommendation engine (age fit, budget fit,
  category match — no black-box scoring) that an advisor runs from a
  lead's "Find Matching Products" button; each match is tracked
  Recommended → Interested/Rejected → Converted.
- **Campaign Management** (`finsetter.campaign`) — build a targeted
  recipient list from any lead filter, then send a real bulk WhatsApp or
  SMS blast through **Twilio's REST API** (or email via a mail template),
  with per-recipient delivery status and campaign-level response/
  conversion rate and ROI. **You must add your own Twilio credentials**
  before any message actually sends — see "WhatsApp / SMS Setup" below.
- **Claims management** (`finsetter.claim`) — file a claim straight from
  a policy, track it Submitted → Under Review → Approved → Settled.
- **Appointments with real Google Calendar sync** (`finsetter.appointment`)
  — books the free 30–45 minute consultation; every appointment creates a
  linked `calendar.event`, so it syncs to the advisor's Google Calendar the
  moment they connect one — see "Google Calendar Setup" below.
- **7 Financial Calculators** (Term Insurance, Health Insurance,
  SIP/Investment, Tax Saving, Retirement Planning, Loan/EMI, Compound
  Interest) — a client-side tool under Finsetter CRM → Tools, or from a
  lead's "Calculators" button. All figures are clearly labelled estimates.
- **Documents & KYC** (`finsetter.document`) — secure attachment storage
  with a Pending → Verified/Rejected workflow, alongside the existing
  consent register, both fully chatter/audit-logged.
- **Customer portal** — customers with a portal login see their own
  Policies, Appointments, Documents and Claims at `/my` — nothing about
  any other customer, enforced by record rules on both sides (backend and
  portal). Grant access from a customer's Contacts record → Action →
  "Grant Portal Access".
- **7 user roles**: Admin (`CRM Administrator`), Manager, Financial
  Advisor, Sales Executive and Customer (portal), plus Team Lead and
  Compliance Officer — see "User Roles" below.

## Project layout

```
finsetter-crm/
├── docker-compose.yml       # Odoo 17 + PostgreSQL 15
├── Dockerfile                # bakes the finsetter_crm addon into the Odoo image
├── config/odoo.conf          # server config (db, addons path, workers, proxy_mode)
├── .env                      # ports, credentials, company info (change before prod!)
├── addons/finsetter_crm/     # the custom Odoo module — see below
└── scripts/                  # up.sh / down.sh / logs.sh / upgrade_module.sh / validate.sh
```

Inside `addons/finsetter_crm/`:

```
models/       crm.lead & res.partner extensions, finsetter.policy,
              finsetter.call.log, finsetter.consent, finsetter.claim,
              finsetter.financial.product, finsetter.lead.product.match,
              finsetter.campaign(.recipient), finsetter.appointment,
              finsetter.document, finsetter.followup.template/log,
              finsetter.messaging (Twilio), crm.team extension,
              res.config.settings extension
controllers/  customer portal routes and protected Twilio status/reply hooks
views/        form/list/kanban/calendar/search views + menus, the dashboard
              & calculators client actions, settings & portal templates
data/         product lines (13 categories), pipeline stages, UTM sources,
              tags, teams, activity types, mail template, cron jobs,
              automation rules, company info
demo/         sample customers, leads, policies, calls, consent records,
              financial products, a campaign, an appointment, a claim
security/     groups (Advisor / Sales Executive / Team Lead / Compliance
              Officer / Manager / CRM Admin) + record rules + access rights
static/src/   the OWL dashboard and the 7-calculator tool (js/xml/scss)
```

## Running it on Windows (double-click, no terminal needed)

If Docker Desktop is installed and running, just double-click:

- **`Start-FinsetterCRM.bat`** — builds the image, starts the containers,
  waits for Odoo to finish loading, then opens `http://localhost:8069` in
  your browser automatically. Safe to run again any time (it won't recreate
  an existing database).
- **`Stop-FinsetterCRM.bat`** — stops the containers (data is kept). Run
  `Stop-FinsetterCRM.bat -v` to also delete the database and start clean
  next time.
- **`View-Logs.bat`** — tails the Odoo container's logs (Ctrl+C to stop
  watching; doesn't stop the containers).
- **`Upgrade-Module.bat`** — after you edit anything under
  `addons\finsetter_crm\`, run this to apply the change without losing data.

These call the same `docker compose` commands as the shell scripts below —
keep the `.bat` files in this folder, next to `docker-compose.yml`.

## Running it (macOS/Linux, or Windows via WSL)

**Requirements:** Docker + Docker Compose, and network access to Docker Hub
to pull the base `odoo:17.0` and `postgres:15` images.

## Validation status

The current local Odoo 17 / PostgreSQL 15 stack has been upgraded with this
module, the Odoo registry loaded successfully, and the login endpoint returned
HTTP 200. Static checks parsed all 39 addon XML files and compiled all 23
Python files; manifest and access-control CSV structure were also checked. A
rollback-only Odoo smoke test verified the 30-day renewal reminder, duplicate
prevention, safe handling of a missing email address, and stopping/cancelling
queued reminders after a reply. External email/Twilio delivery has not been
tested without customer-owned provider credentials and public webhook setup.

1. **Review `.env`** and change `POSTGRES_PASSWORD` / `ODOO_ADMIN_PASSWD`
   before any real deployment (defaults are placeholders).

2. **Build & start:**
   ```bash
   ./scripts/up.sh
   # or directly:
   docker compose up -d --build
   ```
   First boot creates the `finsetter_crm` database and installs the module
   (and its dependencies: base, mail, crm, contacts, sales_team, resource,
   calendar, portal) — this can take a couple of minutes. Watch it with:
   ```bash
   ./scripts/logs.sh
   ```
   Look for `Modules loaded.` with no tracebacks above it.

3. **Log in:** open <http://localhost:8069>, login `admin` / password `admin`
   (Odoo's default for a freshly CLI-created database) — **change it
   immediately** under the user menu → *My Profile* → *Preferences*.

4. **Want it pre-populated?** Demo data (5 sample customers, 5 leads across
   the pipeline, 4 policies including ones renewing in 1/7/15 days, sample
   calls, consent records, financial products across all 13 categories, a
   lead-product match, an appointment, a claim and a draft campaign) ships
   across `demo/*.xml` but is skipped by default (`--without-demo=all` in
   `docker-compose.yml`, for a clean production-style install). To load it
   instead: remove `--without-demo=all` from the `command:` in
   `docker-compose.yml`, then `docker compose down -v && docker compose up
   -d --build` (the `-v` wipes the empty DB volume so it reinstalls with
   demo data).

5. **Open the app:** the app switcher (grid icon, top-left) shows a
  **Finsetter CRM** tile → *Dashboard* is the landing page, with *Sales*
  (Pipeline / New Leads / Existing Leads / Product Matches / Appointments /
  Follow-ups), *Customers*
   (Policies / Claims / Call Logs / Consent Register / Documents & KYC),
   *Marketing* (Campaigns / Testimonials), *Tools* (Financial Calculators)
   and *Reporting* underneath.

6. **Made changes to the module?** Re-apply them without recreating the DB:
   ```bash
   ./scripts/upgrade_module.sh
   ```

7. **Stop:** `./scripts/down.sh` (add `-v` to also delete the database
   volume and start fresh next time).

### Validating the code without Docker

```bash
./scripts/validate.sh
```
Checks every XML file is well-formed, every Python file compiles, and the
  manifest has the required keys. No Odoo/Docker needed. The script requires
  `python3` on PATH; on Windows use Git Bash with a Python installation that
  provides that command.

## WhatsApp / SMS Setup (Twilio)

Campaign sends (`finsetter.campaign`) go out through
[Twilio](https://www.twilio.com/docs/messaging/api/message-resource)'s real
REST API. Nothing sends until you configure it:

1. Create a Twilio account (or use your existing one) and note your
   **Account SID** and **Auth Token** from the Twilio Console.
2. For WhatsApp: either use Twilio's free **WhatsApp Sandbox** number
   (`whatsapp:+14155238886`) for testing, or your own approved WhatsApp
   Business sender for production. For SMS: any Twilio phone number capable
   of sending SMS.
3. In Odoo: **Settings → General Settings → Finsetter CRM**, fill in the
   Account SID, Auth Token, WhatsApp Sender and/or SMS Sender, and save.
4. Build a campaign (Finsetter CRM → Marketing → Campaigns), set its
   target filter, click **Build Recipient List**, then **Send Now**. Each
   recipient's send status (Sent/Failed + error) is tracked on the
   campaign's Recipients tab.

No credentials, no sends — every recipient will just show "Failed: Twilio
is not configured" until step 3 is done. Nothing else in the module
depends on Twilio.

## Lead Follow-ups and Renewal Automation

Sales now has separate **New Leads**, **Existing Leads**, and **Follow-ups**
entries. Existing Leads lists policies and supports appointment scheduling,
current-vs-recommended upgrade comparisons, renewal quotes, payment links,
and marking a policy renewed. The daily renewal sequence uses Email at 30
days, SMS at 15 days, WhatsApp at 7 days, and a Twilio text-to-speech voice
call at 1 day before expiry. A reply, a booked appointment, or a renewal
stops reminders for the current policy cycle. Every attempt is recorded in
Follow-ups with its provider status.

To enable delivery, configure an outgoing mail server in Odoo and set the
Twilio SID/token, SMS/WhatsApp sender(s), Voice-capable caller ID, public
HTTPS CRM URL, and webhook secret under **Settings → General Settings →
Finsetter CRM**. In the Twilio Console, set the inbound messaging webhook
to `https://<public-crm-host>/finsetter/twilio/inbound?token=<webhook-secret>`
using HTTP POST. Outbound status callbacks are attached automatically.
Delivery/read events depend on channel/provider support; email reply detection
also requires an incoming mail server and Odoo catchall/threading to be set
up. The current voice channel is Twilio TTS, not a conversational AI agent;
an AI voice vendor needs its own integration.

## Google Calendar Setup

Every appointment booked in Finsetter CRM (Finsetter CRM → Sales →
Appointments) already creates a linked Odoo `calendar.event`. To make that
sync to the advisor's actual Google Calendar:

1. **Apps → search "Google Calendar" → Install** (ships free with Odoo
   Community — no extra module needed from this build).
2. Follow Odoo's own setup docs to create a Google Cloud OAuth Client
   ID/Secret and enter them under **Settings → General Settings →
   Integrations → Calendar**.
3. Each advisor then connects their own Google account from their user
   preferences (top-right avatar → My Profile → Preferences → Google
   Calendar).

Once connected, no further action is needed — every new/changed
appointment syncs automatically, since it's a standard `calendar.event`
under the hood. This deliberately reuses Odoo's own already-shipped OAuth
flow rather than a custom one built for this module.

## Customer Portal

Give a customer self-service access to their own policies, appointments,
documents and claims:

1. Open their record under **Contacts**.
2. Action menu (⚙) → **Grant Portal Access** → confirm the email → an
   invitation is emailed to them.
3. Once they set a password and log in, they land on their portal home
   (`/my`) with **Your Policies / Your Appointments / Your Documents /
   Your Claims** tiles — each scoped so they only ever see their own
   records (enforced by `ir.rule`, not just hidden in the UI).

## User Roles

| Role (spec) | Odoo group | Access |
|---|---|---|
| Financial Advisor | Advisor | Own leads/policies/calls/consent/claims/appointments/documents |
| Sales Executive | Sales Executive | Lead capture, qualification, appointments & campaigns; read-only on policies/claims |
| — | Team Lead | Everything within their `crm.team` (implies Advisor) |
| — | Compliance Officer | Read-only, company-wide, on the consent register (audit) |
| Manager | Manager | Company-wide reporting, dashboards, campaigns & claims across every team — no system configuration |
| Admin | CRM Administrator | Full access + configuration (assigned to `admin` by default; implies Manager) |
| Customer | *(portal)* | Only their own policies, appointments, documents & claims, via `/my` |

Assign a user's role under **Settings → Users → (user) → Other Rights →
Finsetter CRM**.

## Extending it

- **New product line category:** Finsetter CRM → Configuration → Product
  Line Categories (no code needed).
- **New/real product SKUs:** Finsetter CRM → Configuration → Financial
  Products — replace the illustrative demo entries with Finsetter's real
  products, rates and commissions.
- **Change renewal reminder windows:** edit `_cron_flag_renewals_due` in
  `addons/finsetter_crm/models/finsetter_policy.py` (currently 30/15/7/1
  days), then `./scripts/upgrade_module.sh`.
- **Switch WhatsApp/SMS provider:** all Twilio wiring lives in one file,
  `addons/finsetter_crm/models/finsetter_messaging.py` — swap
  `_finsetter_send_message` for another gateway's API without touching
  campaign logic elsewhere.
- **IRDAI/SEBI reporting exports:** the consent register, policy and claim
  models already carry the fields typically requested in an audit; a
  scheduled export can be added as another `ir.cron` following the same
  pattern as the renewal cron.
