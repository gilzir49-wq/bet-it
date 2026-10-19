# בדיקת עשן בדפדפן אמיתי (Chromium) מול סביבת הבדיקה:
# משתמש חדש נכנס → מהמר → מרענן → ההימור עדיין שם (בשרת ובמסך) → מבטל → הז'יטונים חוזרים.
# אם משהו מזה נכשל – העדכון לא עולה לאתר.
import os, sys, json, time, importlib.util, threading, http.server, functools, secrets, string, urllib.request
from playwright.sync_api import sync_playwright

DB = os.environ['DB_URL']
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
spec = importlib.util.spec_from_file_location('r', os.path.join(ROOT, 'robot.py')); R = importlib.util.module_from_spec(spec)
sys.argv = ['x']; spec.loader.exec_module(R)

# האתר מוגש מקומית, מחובר לסביבת הבדיקה במקום למסד האמיתי
site = os.path.join('/tmp', 'site'); os.makedirs(site, exist_ok=True)
html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
assert "const DB = 'https://buxbet-il-default-rtdb.europe-west1.firebasedatabase.app';" in html, 'DB line changed – update test'
open(os.path.join(site, 'index.html'), 'w', encoding='utf-8').write(html.replace('https://buxbet-il-default-rtdb.europe-west1.firebasedatabase.app', DB))
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8765), functools.partial(http.server.SimpleHTTPRequestHandler, directory=site))
threading.Thread(target=srv.serve_forever, daemon=True).start()

now = int(time.time() * 1000); E = '998' + str(now)[-6:]
R.fb(f'fixtures/{E}', 'PUT', {'lg': 'isr1', 'home': 'Maccabi Haifa', 'away': 'Hapoel Haifa', 'ko': now + 6 * 3600000, 'day': R.day_key(now + 6 * 3600000),
                              'st': 'none', 'h': 0, 'a': 0, 'odds': {'1': 2.0, 'X': 3.0, '2': 4.0, 'cs': {'1-0': 7.0}}})
name = 'smoke' + ''.join(secrets.choice(string.ascii_lowercase) for _ in range(6))
def acct():
    for s, a in (R.fb('acct') or {}).items():
        if a and a.get('name') == name: return s, a
    return None, None
fails = []
def check(cond, msg):
    print(('✅ ' if cond else '❌ ') + msg, flush=True)
    if not cond: fails.append(msg)

try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 390, 'height': 844}, locale='he-IL')
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://127.0.0.1:8765/index.html'); pg.wait_for_selector('#nameIn', timeout=20000)
        pg.fill('#nameIn', name); pg.click('#loginBtn')
        pg.wait_for_function('() => (typeof A!=="undefined" && A) && A.wallet && A.wallet.bal === 500', timeout=20000)
        check(True, 'משתמש חדש נכנס וקיבל 500')
        pg.wait_for_selector('#final.show', timeout=10000); code = pg.locator('#final div[style*="letter-spacing"]').inner_text().replace('-', '').strip()
        check(len(code) == 12, 'הוצג קוד כניסה אישי'); pg.click('#final .btn.sec')
        extra = [pg.context.new_page() for _ in range(3)]                 # עוד 3 לשוניות פתוחות – השמירה חייבת לעבוד
        for x in extra: x.goto('http://127.0.0.1:8765/index.html')
        pg.bring_to_front()
        pg.evaluate(f"() => {{ dayF = S.fixtures['{E}'].day; render(); }}")
        pg.wait_for_selector(f"button.ob[onclick*=\"'{E}','W','1'\"]", timeout=15000)
        pg.click(f"button.ob[onclick*=\"'{E}','W','1'\"]")
        pg.fill('#stakeIn', '50'); pg.click('#betBtn')
        pg.wait_for_function('() => A && A.wallet.bal === 450 && Object.keys(A.bets||{}).length === 1', timeout=20000)
        check(True, 'ההימור נשמר (יתרה 450)')
        sec, a = acct(); check(a and a['wallet']['bal'] == 450 and len(a.get('bets') or {}) == 1, 'ההימור קיים בשרת')
        pg.reload(); pg.wait_for_function('() => (typeof A!=="undefined" && A) && A.wallet && Object.keys(A.bets||{}).length === 1', timeout=20000)
        check(True, 'אחרי רענון – ההימור עדיין שם')
        pg.evaluate(f"() => {{ go('games'); dayF = S.fixtures['{E}'].day; render(); }}")
        check(pg.locator('.mybet').count() >= 1, 'ההימור מוצג בכרטיס המשחק')
        pg.once('dialog', lambda d: d.accept())
        pg.click("a[onclick^=\"cancelBet\"]")
        pg.wait_for_function('() => A && A.wallet.bal === 500 && Object.keys(A.bets||{}).length === 0', timeout=20000)
        check(True, 'ביטול החזיר את הז\'יטונים (500)')
        sec, a = acct(); check(a and a['wallet']['bal'] == 500, 'הביטול נשמר בשרת')
        ctx2 = b.new_context(viewport={'width': 390, 'height': 844}); pg2 = ctx2.new_page()
        pg2.goto('http://127.0.0.1:8765/index.html'); pg2.wait_for_selector('#nameIn', timeout=20000)
        pg2.once('dialog', lambda d: d.accept(code))
        pg2.click("a[onclick^=\"loginWithCode\"]")
        pg2.wait_for_function(f'() => (typeof A!=="undefined" && A) && A.name === "{name}"', timeout=20000)
        check(True, 'כניסה ממכשיר אחר עם הקוד – אותו חשבון'); ctx2.close()
        check(not errs, 'אין שגיאות JavaScript בדף' + (f': {errs[:2]}' if errs else ''))
        b.close()
except Exception as ex:
    check(False, f'הבדיקה נתקעה: {ex}')
finally:
    s, a = acct()
    upd = {f'fixtures/{E}': None}
    if s: upd.update({f'acct/{s}': None, f"names/{a['nk']}": None}); upd.update({f"rc/{a['rc']}": None} if a.get('rc') else {})
    R.fb('', 'PATCH', upd); srv.shutdown()
sys.exit(1 if fails else 0)
