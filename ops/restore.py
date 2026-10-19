# שחזור מגיבוי. שימוש:  python3 restore.py snapshots/latest.json [--acct=<שם משתמש>] [--db=<url>] [--yes]
# בלי --yes רק מציג מה ישוחזר (בטוח). עם --acct משחזר חשבון אחד בלבד.
import json, os, sys, urllib.request
from google.oauth2 import service_account
from google.auth.transport.requests import Request
args = dict(a.split('=', 1) if '=' in a else (a, True) for a in sys.argv[2:])
DB = args.get('--db', 'https://buxbet-il-default-rtdb.europe-west1.firebasedatabase.app')
info = json.loads(os.environ['FIREBASE_SA']) if os.environ.get('FIREBASE_SA') else json.load(open(os.path.expanduser('~/.config/buxbet/sa.json')))
c = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/firebase.database', 'https://www.googleapis.com/auth/userinfo.email']); c.refresh(Request())
snap = json.load(open(sys.argv[1]))
def put(path, body):
    r = urllib.request.Request(f'{DB}/{path}.json', method='PUT', data=json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + c.token})
    urllib.request.urlopen(r, timeout=60).read()
if '--acct' in args:
    hit = [(s, a) for s, a in (snap.get('acct') or {}).items() if a and a.get('name') == args['--acct']]
    if not hit: sys.exit('לא נמצא חשבון בשם הזה בגיבוי')
    s, a = hit[0]; print(f"ישוחזר: {a['name']} · יתרה {a['wallet']['bal']} · {len(a.get('bets') or {})} הימורים")
    if '--yes' in args: put(f'acct/{s}', a); put(f"names/{a['nk']}", a['pid']); print('שוחזר ✅')
else:
    print(f"ישוחזר כל המסד: {len(snap.get('acct') or {})} חשבונות")
    if '--yes' in args: put('', snap); print('שוחזר ✅')
