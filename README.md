# WhatsApp Lead Generation Bot (Twilio Sandbox + Excel + Gemini-ready)

Natural-conversation WhatsApp bot for lead generation using Twilio WhatsApp Sandbox, JSON-driven dialogue flows, and optional Google Gemini for friendly clarifications. Contacts are managed in an Excel file.

## Features
- JSON-driven conversation flow per product (easily swap scripts)
- Eligibility gating and Calendly booking for qualified leads
- Optional Gemini fallback for unclear replies (guardrailed)
- Excel-based outreach with dry-run and sandbox safety guard
- Persistent conversation state across restarts
- Simple stats endpoint and PII-redacted logs

## Requirements
- Python 3.11+
- Twilio account with WhatsApp Sandbox enabled
- A verified WhatsApp recipient number in the Sandbox

## Setup
1. Install dependencies:
```bash
uv sync  # or: pip install -e .
```

2. Create `.env` in project root:
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886  # Sandbox from Twilio
TEST_RECIPIENT_NUMBER=whatsapp:+9715XXXXXXXX  # your verified number

FLASK_SECRET_KEY=dev-secret-key-change-in-production

# Feature flags
USE_GEMINI=false
PRODUCT_KEY=mortgage
TWILIO_SANDBOX=true

# Optional: override locations
# CONTACTS_FILE=data/contacts.xlsx
# DIALOGUE_DIR=dialogue
# DIALOGUE_FILE=dialogue/mortgage.flow.json

# If USE_GEMINI=true
GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

3. Prepare contacts Excel at `data/contacts.xlsx` with columns:
- `FullName`, `PhoneNumber` (optional: `Status`, `LastContacted`, `Product`)

## Run the Webhook Server
```bash
python app.py
```
Expose your local server to the internet (e.g., with ngrok) and configure Twilio Sandbox Inbound Webhook to `POST https://<your-ngrok>/webhook`.

Health and stats:
- `GET /health`
- `GET /stats`

## Outreach (Initial Message Broadcast)
Dry-run first:
```bash
python send_outreach.py --limit 5 --dry-run
```
Send for real (Sandbox guard restricts to TEST_RECIPIENT_NUMBER):
```bash
python send_outreach.py --limit 5 --delay 3
```

The initial message template is sourced from the `INITIAL.message_template` in the active dialogue flow.

## Dialogue Flows (Multi-product)
- Flows live in `dialogue/{product}.flow.json`
- Active product selected via `PRODUCT_KEY`
- Example provided: `dialogue/mortgage.flow.json`

To add a new product:
1. Copy `dialogue/mortgage.flow.json` → `dialogue/<your_product>.flow.json`
2. Adjust `product_hook`, `calendly_link`, and `states`
3. Set `PRODUCT_KEY=<your_product>` in `.env`

## Gemini Clarifications (Optional)
The bot stays deterministic for eligibility and state transitions. If a user response is unclear, and `USE_GEMINI=true`, Gemini generates a short, friendly clarification guiding the user to the expected reply.

## Notes
- Logs are written to `logs/` with minimal PII (redacted phone numbers).
- Conversation state persists to `data/conversations/` (rotated daily JSON files).

## Testing
- Verify configuration:
```bash
python test_config.py
```
- Manual end-to-end via Twilio Sandbox using your verified WhatsApp number.
