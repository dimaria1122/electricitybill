# Electricity Bill Monitor

Local-only electricity balance monitor for one authorized HuiXinYiXiao dorm room.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill your current `SYNJONES_AUTH` token from Reqable. Replace `ROOM=your_authorized_room_id` with the room identifier you are authorized to query. Do not commit `.env`.

## Run

```bash
uvicorn electricitybill.app:app --reload
```

Open `http://127.0.0.1:8000`.

## Verify one query

Click `立即刷新` on the page, or wait for the startup query. If the token is invalid, the dashboard shows an auth error and you should refresh the token in `.env` and restart the server.

## Tests

```bash
python -m pytest tests -v
```

## Notes

Scheduled collection runs only while the local server process is active. If your Mac sleeps or the server stops, collection pauses until the app is running again.

## Security

- Only query rooms you are authorized to query.
- The token stays in local `.env`.
- The app does not store your account password.
- The app does not automate payment or bypass app protections.
