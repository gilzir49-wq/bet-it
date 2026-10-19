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
last = subprocess.run(['git', 'log', '-1', '--format=%ct', 'origin/backups'], capture_output=True, text=True).stdout.strip()
if not last or time.time() - int(last) > 3 * 3600: problems.append('הגיבוי האחרון ישן מ-3 שעות')
print('\n'.join(problems) or 'הכול תקין ✅'); sys.exit(1 if problems else 0)
