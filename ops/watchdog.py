# שומר-לילה: נכשל (ו-GitHub שולח מייל) אם משהו לא תקין
import json, time, urllib.request, urllib.error, subprocess, sys
DB = 'https://buxbet-il-default-rtdb.europe-west1.firebasedatabase.app'
problems = []
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'watchdog'}), timeout=20) as r: return r.status, r.read().decode()
try:
    st, body = get('https://bet-it.web.app/')
    if st != 200 or 'BET-IT' not in body: problems.append('האתר bet-it.web.app לא עולה כמו שצריך')
except Exception as e: problems.append(f'האתר לא זמין: {e}')
try:
    ra = json.loads(get(DB + '/pub/meta/robotAt.json')[1] or '0') or 0
    age = (time.time() * 1000 - ra) / 60000
    if age > 20: problems.append(f'הרובוט לא עדכן כבר {age:.0f} דקות')
except Exception as e: problems.append(f'אין גישה למסד: {e}')
try:
    urllib.request.urlopen(DB + '/acct.json', timeout=20); problems.append('🚨 חוקי האבטחה פתוחים – אפשר לקרוא חשבונות!')
except urllib.error.HTTPError as e:
    if e.code != 401: problems.append(f'בדיקת אבטחה החזירה {e.code}')
# תקיפה עצמית חיה (קריאה/כתיבה שחייבות להיחסם – לא משאירות שום דבר במסד)
def denied(method, path, body=None):
    try:
        r = urllib.request.Request(f'{DB}/{path}.json', method=method, data=None if body is None else json.dumps(body).encode())
        urllib.request.urlopen(r, timeout=20); return False
    except urllib.error.HTTPError as e: return e.code in (401, 403)
    except Exception: return True
for name, m, path, body in [('קריאת כל החשבונות', 'GET', 'acct', None), ('קריאת קודי כניסה', 'GET', 'rc', None),
                            ('קריאת כל הליגות', 'GET', 'lgdef', None), ('קריאת מפתחות מנהל', 'GET', 'adminKeys', None),
                            ('זיוף תוצאת משחק', 'PATCH', 'fixtures/1', {'st': 'finished'}), ('זיוף טבלה', 'PUT', 'pub/standings/bank', 0),
                            ('כתיבה לנתיב לא מוכר', 'PUT', 'hack', 1), ('פתיחת חשבון עם מיליון', 'PUT', 'acct/s' + 'A' * 48, {'name': 'x', 'wallet': {'bal': 999999}})]:
    if not denied(m, path, body): problems.append(f'🚨 פרצה חיה: {name} – לא נחסם!')
last = subprocess.run(['git', 'log', '-1', '--format=%ct', 'origin/backups'], capture_output=True, text=True).stdout.strip()
if not last or time.time() - int(last) > 3 * 3600: problems.append('הגיבוי האחרון ישן מ-3 שעות')
print('\n'.join(problems) or 'הכול תקין ✅'); sys.exit(1 if problems else 0)
