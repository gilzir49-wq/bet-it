# מעלה את database.rules.json למסד (DB_URL) עם מפתח השירות (FIREBASE_SA)
import json, os, urllib.request
from google.oauth2 import service_account
from google.auth.transport.requests import Request
c = service_account.Credentials.from_service_account_info(json.loads(os.environ['FIREBASE_SA']),
    scopes=['https://www.googleapis.com/auth/firebase.database', 'https://www.googleapis.com/auth/userinfo.email']); c.refresh(Request())
body = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database.rules.json'), 'rb').read()
r = urllib.request.Request(os.environ['DB_URL'] + '/.settings/rules.json', method='PUT', data=body, headers={'Authorization': 'Bearer ' + c.token})
print('rules deployed:', urllib.request.urlopen(r, timeout=30).read().decode())
