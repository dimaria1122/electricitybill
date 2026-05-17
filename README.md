# Electricity Bill Monitor

Local-only electricity balance monitor for one authorized HuiXinYiXiao dorm room.

## Setup on macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill your current `SYNJONES_AUTH` token from Reqable. Replace `ROOM=your_authorized_room_id` with the room identifier you are authorized to query. Do not commit `.env`.

Run locally:

```bash
uvicorn electricitybill.app:app --reload
```

Open `http://127.0.0.1:8000`.

You can also use the helper script:

```bash
chmod +x scripts/run-macos-linux.sh
./scripts/run-macos-linux.sh
```

## Setup on Windows

From PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`, then run:

```powershell
uvicorn electricitybill.app:app --host 127.0.0.1 --port 8000
```

Or use the helper script:

```powershell
.\scripts\run-windows.ps1
```

## Raspberry Pi / LAN usage

On Raspberry Pi, use the same macOS/Linux setup. To access the dashboard from another device on the same network, bind to all interfaces:

```bash
HOST=0.0.0.0 PORT=8000 ./scripts/run-macos-linux.sh
```

Then open:

```text
http://<raspberry-pi-ip>:8000
```

Keep `.env` and `electricity.db` on the Raspberry Pi. They are intentionally ignored by git.

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

## Future: automatic login

Automatic login can be added later if the HuiXinYiXiao login endpoint remains a simple username/password flow. Before implementing it, confirm whether the login API uses CAPTCHA, SMS verification, device fingerprinting, or other protections. This project should not bypass those protections.
