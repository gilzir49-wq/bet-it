# גיבוי מלא של מסד BUX BET (כולל חשבונות, הימורים, יתרות והיסטוריה). רץ כל שעה.
import json, os, datetime, urllib.request
from google.oauth2 import service_account
from google.auth.transport.requests import Request
DB = os.environ.get('DB_URL', 'https://buxbet-il-default-rtdb.europe-west1.firebasedatabase.app')
c = service_account.Credentials.from_service_account_info(json.loads(os.environ['FIREBASE_SA']),
    scopes=['https://www.googleapis.com/auth/firebase.database', 'https://www.googleapis.com/auth/userinfo.email'])
c.refresh(Request())
r = urllib.request.Request(f'{DB}/.json?format=export', headers={'Authorization': 'Bearer ' + c.token})
data = json.loads(urllib.request.urlopen(r, timeout=60).read().decode())
os.makedirs('snapshots', exist_ok=True)  # קבצים זמניים – מוצפנים לפני שמירה
json.dump(data, open('snapshots/latest.json', 'w'), ensure_ascii=False, sort_keys=True, indent=0)
day = datetime.datetime.utcnow().strftime('%Y-%m-%d')
json.dump(data, open(f'snapshots/daily-{day}.json', 'w'), ensure_ascii=False, sort_keys=True, indent=0)   # עותק יומי נפרד
n = len((data or {}).get('acct') or {})
print(f'backup ok: {n} accounts, {sum(len((a or {}).get("bets") or {}) for a in ((data or {}).get("acct") or {}).values())} bets')
