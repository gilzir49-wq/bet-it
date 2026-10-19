# בדיקת חדירה ל-BUX BET: תוקף בלי הרשאות (REST ישיר), מנסה לרמות.
import json, time, secrets, string, urllib.request, urllib.error, sys, os, importlib.util
DB = os.environ['DB_URL']
spec = importlib.util.spec_from_file_location('r', os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','robot.py')); R = importlib.util.module_from_spec(spec)
sys.argv = ['x']; spec.loader.exec_module(R)   # רק בשביל fb() עם הרשאות מנהל להכנת נתוני בדיקה

def req(method, path, body=None):
    r = urllib.request.Request(f'{DB}/{path}.json', method=method, data=None if body is None else json.dumps(body).encode(),
                               headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(r, timeout=20) as x: return x.status, json.loads(x.read().decode() or 'null')
    except urllib.error.HTTPError as e: return e.code, None
AZM = string.ascii_letters + string.digits; AZ = string.ascii_lowercase + string.digits
rs = lambda n, a: ''.join(secrets.choice(a) for _ in range(n))
SV = {'.sv': 'timestamp'}
results = []
def check(name, cond, expect):
    ok = cond == expect; results.append((ok, name)); print(('✅' if ok else '❌ FAIL'), name, flush=True)

now = int(time.time() * 1000); OPEN, LOCKED = '999000001', '999000002'; RUN = rs(5, AZ)
day = R.day_key(now + 2 * 86400e3)
R.fb('', 'PATCH', {f'fixtures/{OPEN}': {'lg': 'isr1', 'home': 'Maccabi Haifa', 'away': 'Hapoel Haifa', 'ko': now + 2 * 86400000, 'day': day, 'st': 'none', 'h': 0, 'a': 0,
                                        'odds': {'1': 1.8, 'X': 3.4, '2': 4.1, 'cs': {'1-0': 6.5, '2-1': 8.0}}},
                   f'fixtures/{LOCKED}': {'lg': 'isr1', 'home': 'Hapoel Tel Aviv', 'away': 'Beitar Jerusalem', 'ko': now + 60000, 'day': R.day_key(now), 'st': 'none', 'h': 0, 'a': 0,
                                          'odds': {'1': 2.0, 'X': 3.0, '2': 3.5}}})

def new_acct(name):
    sec, pid, nk = 's' + rs(48, AZM), 'p' + rs(16, AZ), name.lower().replace(' ', '')
    st, _ = req('PATCH', '', {f'names/{nk}': pid, f'acct/{sec}': {'name': name, 'nk': nk, 'pid': pid, 'joined': SV, 'wallet': {'bal': 500, 'op': 'init'}}})
    return st, sec, pid, nk

print('--- קריאה')
check('קריאת כל החשבונות (acct)', req('GET', 'acct')[0], 401)
check('קריאת שורש המסד', req('GET', '')[0], 401)
check('קריאת מפתחות מנהל', req('GET', 'adminKeys')[0], 401)
check('קריאת בקשות שחזור', req('GET', 'recoverReq')[0], 401)
check('קריאת תצוגת מנהל עם מפתח מזויף', req('GET', 'adminView/k' + rs(40, AZM))[0], 401)

print('--- זיוף תוצאות ונתונים ציבוריים')
check('זיוף תוצאת משחק', req('PATCH', f'fixtures/{OPEN}', {'h': 5, 'st': 'finished'})[0], 401)
check('זיוף יחס', req('PUT', f'fixtures/{OPEN}/odds/1', 50)[0], 401)
check('זיוף טבלת דירוג', req('PUT', 'pub/standings/bank', 0)[0], 401)
check('זיוף "הימורים שנחשפו"', req('PUT', 'pub/revealed/x', {'a': 1})[0], 401)
check('זיוף טבלת ליגה', req('PUT', 'pub/tables/isr1', {})[0], 401)
check('כתיבה לנתיב לא מוגדר', req('PUT', 'hack', 1)[0], 401)

print('--- יצירת חשבון')
sec0, pid0 = 's' + rs(48, AZM), 'p' + rs(16, AZ)
check('פתיחת חשבון עם 1,000,000 ז\'יטונים', req('PATCH', '', {f'names/pentest_rich{RUN}': pid0, f'acct/{sec0}': {'name': 'pentest_rich'+RUN, 'nk': 'pentest_rich'+RUN, 'pid': pid0, 'joined': SV, 'wallet': {'bal': 1000000, 'op': 'init'}}})[0], 401)
check('פתיחת חשבון עם הימורים/זכיות מוכנים', req('PATCH', '', {f'names/pentest_x{RUN}': pid0, f'acct/{sec0}': {'name': 'pentest_x'+RUN, 'nk': 'pentest_x'+RUN, 'pid': pid0, 'joined': SV, 'wallet': {'bal': 500, 'op': 'init'}, 'settled': {'b1': {'st': 'won', 'pay': 9999}}}})[0], 401)
check('פתיחת חשבון בלי לתפוס שם', req('PUT', f'acct/{sec0}', {'name': 'pentest_y'+RUN, 'nk': 'pentest_y'+RUN, 'pid': pid0, 'joined': SV, 'wallet': {'bal': 500, 'op': 'init'}})[0], 401)
st, A, Apid, Ank = new_acct('pentest_a'+RUN); check('פתיחת חשבון תקין (500)', st, 200)
st, B, Bpid, Bnk = new_acct('pentest_b'+RUN); check('פתיחת חשבון תקין שני', st, 200)
check('התחזות: פתיחת חשבון עם שם תפוס', new_acct('pentest_a'+RUN)[0], 401)
check('התחזות: אותו שם באותיות גדולות', new_acct('PENTEST_A'+RUN.upper())[0], 401)
check('דריסת חשבון קיים (איפוס יתרה)', req('PUT', f'acct/{A}', {'name': 'pentest_a'+RUN, 'nk': Ank, 'pid': Apid, 'joined': SV, 'wallet': {'bal': 500, 'op': 'init'}})[0], 401)
check('מחיקת חשבון', req('DELETE', f'acct/{A}')[0], 401)

print('--- יתרה')
check('שינוי יתרה ישיר', req('PUT', f'acct/{A}/wallet/bal', 99999)[0], 401)
check('שינוי ארנק שלם', req('PUT', f'acct/{A}/wallet', {'bal': 99999, 'op': 'init'})[0], 401)
check('כתיבת "זכייה" מזויפת (settled)', req('PUT', f'acct/{A}/settled/b123', {'st': 'won', 'pay': 5000})[0], 401)
check('קבלת מענק שבועי מזויף', req('PATCH', f'acct/{A}/wallet', {'wk': '2099-01-01', 'bal': 550})[0], 401)

def bet(sec, bid, bal, e=OPEN, m='W', p='1', s=50, o=1.8, dec=None, extra=None):
    b = {'e': e, 'm': m, 'p': p, 's': s, 'o': o, 'at': SV}; b.update(extra or {})
    upd = {f'acct/{sec}/bets/{bid}': b, f'acct/{sec}/wallet/bal': bal - (s if dec is None else dec), f'acct/{sec}/wallet/op': 'b:' + bid}
    return upd
print('--- הימורים')
check('הימור ביחס מזויף (50 במקום 1.8)', req('PATCH', '', bet(A, 'bpentest01', 500, o=50))[0], 401)
check('הימור בלי להוריד מהיתרה', req('PATCH', '', bet(A, 'bpentest02', 500, dec=0))[0], 401)
check('הימור שמוריד פחות מהסכום', req('PATCH', '', bet(A, 'bpentest03', 500, s=100, dec=1))[0], 401)
check('הימור מעל היתרה (600 מתוך 500)', req('PATCH', '', bet(A, 'bpentest04', 500, s=600))[0], 401)
check('הימור בסכום שלילי', req('PATCH', '', bet(A, 'bpentest05', 500, s=-100))[0], 401)
check('הימור בסכום לא שלם', req('PATCH', '', bet(A, 'bpentest06', 500, s=10.5))[0], 401)
check('הימור על משחק נעול (דקה לפני)', req('PATCH', '', bet(A, 'bpentest07', 500, e=LOCKED, o=2.0))[0], 401)
check('הימור על משחק שלא קיים', req('PATCH', '', bet(A, 'bpentest08', 500, e='123456'))[0], 401)
check('הימור עם נתיב זדוני במזהה משחק', req('PATCH', '', bet(A, 'bpentest09', 500, e='../acct'))[0], 401)
check('הימור על תוצאה לא חוקית (9-9)', req('PATCH', '', bet(A, 'bpentest10', 500, m='CS', p='9-9', o=6.5))[0], 401)
check('הימור עם שדה נוסף ("won")', req('PATCH', '', bet(A, 'bpentest11', 500, extra={'won': True}))[0], 401)
check('הימור תקין', req('PATCH', '', bet(A, 'bpentest12', 500))[0], 200)
check('שידור חוזר של אותו הימור (הורדה כפולה/עקיפה)', req('PATCH', '', bet(A, 'bpentest12', 450))[0], 401)
check('שינוי סכום של הימור קיים', req('PUT', f'acct/{A}/bets/bpentest12/s', 5)[0], 401)
check('שינוי יחס של הימור קיים', req('PUT', f'acct/{A}/bets/bpentest12/o', 40)[0], 401)
check('הימור תוצאה מדויקת תקין', req('PATCH', '', bet(A, 'bpentest13', 450, m='CS', p='2-1', o=8.0, s=10))[0], 200)

print('--- ביטול')
canc = lambda sec, bid, bal, s: {f'acct/{sec}/bets/{bid}': None, f'acct/{sec}/wallet/bal': bal + s, f'acct/{sec}/wallet/op': 'c:' + bid}
check('ביטול עם החזר מנופח', req('PATCH', '', canc(A, 'bpentest13', 440, 500))[0], 401)
check('ביטול תקין', req('PATCH', '', canc(A, 'bpentest13', 440, 10))[0], 200)
check('ביטול כפול (החזר פעמיים)', req('PATCH', '', canc(A, 'bpentest13', 450, 10))[0], 401)
check('החזר בלי למחוק את ההימור', req('PATCH', '', {f'acct/{A}/wallet/bal': 500, f'acct/{A}/wallet/op': 'c:bpentest12'})[0], 401)

print('--- ג\'וקר')
j1 = bet(A, 'bpentest14', 450, s=10, extra={'j': True}); j1[f'acct/{A}/jokers/{day}'] = 'bpentest14'
check('ג\'וקר ראשון ביום', req('PATCH', '', j1)[0], 200)
j2 = bet(A, 'bpentest15', 440, s=10, extra={'j': True}); j2[f'acct/{A}/jokers/{day}'] = 'bpentest15'
check('ג\'וקר שני באותו יום', req('PATCH', '', j2)[0], 401)
check('ג\'וקר בלי לרשום אותו', req('PATCH', '', bet(A, 'bpentest16', 440, s=10, extra={'j': True}))[0], 401)

print('--- התחזות לשחקן אחר')
check('הימור בחשבון של B עם מפתח מזויף', req('PATCH', '', bet('s' + rs(48, AZM), 'bpentest17', 500))[0], 401)
check('קריאת חשבון לפי מזהה ציבורי (pid)', req('GET', f'acct/{Bpid}')[0], 401)
st, data = req('GET', f'names/{Bnk}'); check('מהשם אפשר לדעת רק מזהה ציבורי (לא מפתח)', (st, data == Bpid), (200, True))
st, rv = req('GET', f'pub/revealed/{OPEN}'); check('הימורים של אחרים מוסתרים לפני הנעילה', rv, None)

print('--- מנהל')
check('פעולת מנהל עם מפתח מזויף', req('PUT', f'adminOps/k{rs(40, AZM)}/o1', {'t': 'adjust', 'pid': Apid, 'd': 9999, 'at': SV})[0], 401)
check('רישום מפתח מנהל חדש', req('PUT', f'adminKeys/k{rs(40, AZM)}', True)[0], 401)
check('בקשת שחזור לשם שלא קיים', req('PUT', f'recoverReq/s{rs(48, AZM)}', {'nk': 'nobody_here', 'at': SV})[0], 401)

st, a = req('GET', f'acct/{A}')
check('יתרה סופית של A נכונה (500−50−10 = 440)', (a or {}).get('wallet', {}).get('bal'), 440)

# ניקוי
R.fb('', 'PATCH', {f'acct/{A}': None, f'acct/{B}': None, f'names/{Ank}': None, f'names/{Bnk}': None,
                   f'fixtures/{OPEN}': None, f'fixtures/{LOCKED}': None, f'pub/profiles/{Apid}': None, f'pub/profiles/{Bpid}': None, f'pub/revealed/{OPEN}': None})
print(f"\nסיכום: {sum(ok for ok, _ in results)}/{len(results)} בדיקות עברו")
sys.exit(0 if all(ok for ok, _ in results) else 1)
