# Electricity Bill Monitor Design

Date: 2026-05-16

## Purpose

Build a local Mac application that monitors one dorm room's electricity balance from the HuiXinYiXiao app backend. The first version runs locally, queries the verified bill endpoint every 30 minutes, stores readings in SQLite, and shows balance and usage trends in a local browser page.

The goal is to understand whether the dorm's electricity usage is unusually high by tracking balance changes over time, not to bypass authentication or query other rooms.

## Confirmed Data Source

The Android Reqable capture confirmed that the app calls this endpoint when checking a room balance:

```text
POST http://121.251.19.62/charge/feeitem/getThirdData
Content-Type: application/x-www-form-urlencoded
synjones-auth: bearer <token>
```

Request body:

```text
feeitemid=261&type=IEC&level=1&room=<authorized_room_id>
```

Successful response shape:

```json
{
  "msg": "success",
  "code": 200,
  "map": {
    "showData": {
      "信息": "房间名称: <authorized_room_id> 剩余金额:105.123571"
    },
    "data": {
      "aid": "<account_aid>",
      "account": "<account_id>",
      "room": "<authorized_room_id>"
    }
  }
}
```

The balance is parsed from `map.showData.信息` using the `剩余金额:<number>` pattern.

## Authentication Decision

Testing without login credentials returned `401` with a missing-token/authentication failure. The endpoint requires a valid `synjones-auth` bearer token.

Version 1 uses a manual token workflow:

1. The user captures or copies the current `synjones-auth` token.
2. The token is stored locally in `.env`.
3. The app uses the token for scheduled queries.
4. If the server returns `401`, the app records token failure and tells the user to refresh the token.
5. Token lifetime is observed before deciding whether automatic login is worth implementing.

The app will not store the HuiXinYiXiao username/password in version 1.

## Scope

### In scope

- Run on the user's Mac.
- Query the verified endpoint every 30 minutes.
- Query immediately once when the service starts.
- Allow manual refresh from the browser page.
- Store readings in local SQLite.
- Display a local web dashboard with:
  - current balance;
  - last successful update time;
  - token status;
  - balance curve;
  - per-reading balance difference;
  - last 24 hours consumption;
  - last 7 days average daily consumption;
  - estimated days remaining based on recent consumption.
- Avoid logging or displaying the token.

### Out of scope for version 1

- Automatic login with account/password.
- CAPTCHA, SMS, certificate pinning, or anti-bot bypass.
- Querying rooms without authorization.
- Comparing with other dorms unless those dorms explicitly provide their own authorized data.
- Cloud deployment.
- Payment or recharge automation.

## Architecture

Use Python + FastAPI + SQLite + a browser dashboard.

```text
.env configuration
  -> FastAPI application
  -> scheduler triggers query every 30 minutes
  -> HuiXinYiXiao client calls getThirdData
  -> parser extracts balance
  -> SQLite stores reading and status
  -> browser dashboard renders charts and metrics
```

## Components

### Configuration

Reads `.env` values:

```env
SYNJONES_AUTH=bearer xxx
ROOM=your_authorized_room_id
FEEITEM_ID=261
QUERY_INTERVAL_MINUTES=30
```

Configuration validation checks that required values exist and that the interval is positive. The token value is never printed.

### HuiXinYiXiao client

Responsibilities:

- Send the POST request to `http://121.251.19.62/charge/feeitem/getThirdData`.
- Include `synjones-auth` and `Content-Type: application/x-www-form-urlencoded`.
- Send form fields `feeitemid`, `type=IEC`, `level=1`, and `room`.
- Classify responses into:
  - success;
  - token/auth failure;
  - network failure;
  - unexpected response;
  - parse failure.

### Parser

Responsibilities:

- Read `map.showData.信息` from the JSON response.
- Extract the room number and balance from the Chinese display string.
- Return a typed result with `balance`, `room`, and raw display text for debugging.
- Fail clearly if the expected balance pattern is missing.

### Storage

SQLite stores durable local history.

Proposed tables:

```sql
readings(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room TEXT NOT NULL,
  balance REAL NOT NULL,
  display_text TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'api'
)

query_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status TEXT NOT NULL,
  message TEXT NOT NULL,
  recorded_at TEXT NOT NULL
)
```

The app stores successful readings and failed query events. Token failures are visible in status but do not delete existing readings.

### Scheduler

Responsibilities:

- Run one query immediately when the service starts.
- Run another query every 30 minutes.
- Catch errors and record them instead of crashing the service.
- Avoid overlapping queries if a previous request is still running.

### API

Endpoints:

- `GET /api/status`
  - current balance;
  - last successful reading time;
  - last query status;
  - estimated token expiration if decodable from JWT;
  - token validity state.
- `GET /api/readings`
  - historical readings for charts.
- `POST /api/refresh`
  - manually trigger one query.
- `GET /`
  - browser dashboard.

### Dashboard

The dashboard is a local-only web page. It displays summary cards and charts:

- Current balance.
- Last updated time.
- Token status.
- Balance over time.
- Consumption between readings.
- Last 24 hours consumption.
- Last 7 days average daily consumption.
- Estimated days remaining.

Charting can use a CDN-loaded chart library for version 1 if the Mac has internet access, or a simple SVG/canvas fallback if needed.

## Data Calculations

- Per-reading consumption: previous balance minus current balance.
- Negative consumption means the balance increased, likely due to recharge; the UI should mark it as recharge rather than usage.
- Last 24 hours consumption: first balance in the 24-hour window minus latest balance, adjusted to ignore recharge jumps.
- Last 7 days average daily consumption: total positive consumption in the last 7 days divided by the number of covered days.
- Estimated days remaining: current balance divided by recent average daily consumption. If recent consumption is zero or unavailable, show `insufficient data`.

## Error Handling

- `401` or authentication message: mark token invalid and tell the user to update `.env` and restart the service.
- Network timeout: record query event and keep serving existing data.
- Unexpected JSON: record parse failure and include a safe message without token data.
- Missing balance pattern: record parse failure and show that the response format may have changed.
- Empty history: dashboard shows setup guidance instead of empty charts.

## Security

- `.env` is ignored by git.
- Token is never committed, displayed, or logged.
- HTTP request logs redact authentication headers.
- The application only supports the configured room by default.
- No password-based auto-login in version 1.
- No bypassing app protections or querying unauthorized rooms.

## Verification Plan

1. Create `.env` with the user's current token and room configuration.
2. Run a one-time query and confirm a balance is parsed.
3. Confirm a reading is inserted into SQLite.
4. Start the FastAPI server and open the dashboard.
5. Trigger manual refresh and confirm a new query event/reading appears.
6. Temporarily use an invalid token and confirm the dashboard reports token failure without exposing token text.
7. Restore the valid token and confirm querying works again.

## Implementation Order

1. Project scaffolding and dependency setup.
2. Configuration and `.env.example`.
3. HuiXinYiXiao client and balance parser.
4. SQLite storage.
5. Manual one-shot query path.
6. FastAPI API endpoints.
7. Scheduler.
8. Dashboard and charts.
9. Verification and usage instructions.

## Open Follow-up After Version 1

After observing token lifetime, decide whether to add automatic login. If token lasts long enough, manual token refresh remains the safer and simpler workflow.
