# בדיקת חדירה ל-BUX BET: תוקף בלי הרשאות (REST ישיר), מנסה לרמות.
import json, time, secrets, string, urllib.request, urllib.error, urllib.parse, sys, os, importlib.util
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

RCA = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
CODES = {}
def new_acct(name):
    sec, pid, nk, rc = 's' + rs(48, AZM), 'p' + rs(16, AZ), name.lower().replace(' ', ''), rs(12, RCA)
    st, _ = req('PATCH', '', {f'names/{nk}': pid, f'rc/{rc}': sec, f'acct/{sec}': {'name': name, 'nk': nk, 'pid': pid, 'rc': rc, 'joined': SV, 'wallet': {'bal': 500, 'op': 'init'}}})
    CODES[sec] = rc
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
check('הימור על תוצאה לא חוקית (12-0)', req('PATCH', '', bet(A, 'bpentest10', 500, m='CS', p='12-0', o=6.5))[0], 401)
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
# משחק נדחה → הרובוט החזיר את הסכום (void) → המשחק חזר ללוח: ביטול היה נותן החזר כפול
check('הימור לפני דחייה', req('PATCH', '', bet(A, 'bpentest18', 450, s=20))[0], 200)
R.fb('', 'PATCH', {f'acct/{A}/settled/bpentest18': {'st': 'void', 'pay': 20, 'at': R.now_ms()}, f'acct/{A}/wallet/bal': 450})
check('החזר כפול: ביטול הימור שכבר הוחזר (משחק נדחה וחזר)', req('PATCH', '', canc(A, 'bpentest18', 450, 20))[0], 401)
check('החזר כפול: ביטול עם ג\'וקר/בלי – גם מחיקת ההימור לבד', req('DELETE', f'acct/{A}/bets/bpentest18')[0], 401)

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

print('--- הזרקת קוד דרך שמות')
for bad in ['x"onclick', "a`b", 'a&quot;b', 'a;b', 'a{b}', 'a\\b', '<b>x']:
    check(f'שם שחקן עם תווים מסוכנים: {bad}', new_acct('pt' + RUN + bad)[0], 401)
check('שם ליגה עם תווים מסוכנים', req('PATCH', '', {f'lgdef/{rs(6, RCA)}': {'n': 'a"onclick=x', 'at': SV}})[0], 401)
for nm, bad in [('היפוך כיוון RLO', '\u202e'), ('סימן כיוון בלתי נראה RLM', '\u200f'), ('רווח באורך אפס', '\u200b'), ('BOM', '\ufeff')]:
    check(f'התחזות עם תו בלתי נראה בשם ({nm})', new_acct('pentest_a' + RUN + bad)[0], 401)
check('שם ליגה עם תו בלתי נראה', req('PATCH', '', {f'lgdef/{rs(6, RCA)}': {'n': 'league\u200f', 'at': SV}})[0], 401)
st, G, Gpid, Gnk = new_acct('גל ' + RUN); check('שם תקין בעברית עם רווח עדיין עובד', st, 200)

print('--- קוד כניסה אישי')
check('קריאת כל הקודים (rc)', req('GET', 'rc')[0], 401)
st, got = req('GET', f'rc/{CODES[A]}'); check('כניסה עם הקוד הנכון מחזירה את החשבון', got == A, True)
check('ניחוש קוד אקראי לא מחזיר חשבון', req('GET', f'rc/{rs(12, RCA)}')[1], None)
# הקוד = הלינק האישי = סיסמה: אסור שתהיה דרך לרשום/לחפש קודים בלי לדעת קוד מלא
for q in ['shallow=true', 'orderBy="$key"&limitToFirst=1', 'orderBy="$value"&equalTo="' + A + '"', 'orderBy="$key"&startAt="' + CODES[A][:6] + '"&limitToFirst=1']:
    try:
        with urllib.request.urlopen(f'{DB}/rc.json?{urllib.parse.quote(q, safe="=&$")}', timeout=20) as x: st = x.status
    except urllib.error.HTTPError as e: st = e.code
    check(f'חיפוש קודים בשאילתה ({q.split("=")[0]}…)', st, 401)
check('קוד חלקי (11 תווים)', req('GET', f'rc/{CODES[A][:11]}')[0], 401)
check('קוד באותיות קטנות לא עוקף את התבנית', req('GET', f'rc/{CODES[A].lower()}')[0], 401)
check('קוד עם נתיב (rc/<קוד>/..)', req('GET', f'rc/{CODES[A]}/x')[1], None)
check('דריסת קוד קיים כך שיצביע לחשבון אחר', req('PUT', f'rc/{CODES[A]}', B)[0], 401)
check('קוד חדש שמצביע לחשבון של מישהו אחר', req('PUT', f'rc/{rs(12, RCA)}', B)[0], 401)
check('החלפת הקוד של חשבון קיים', req('PATCH', '', {f'acct/{A}/rc': (c2 := rs(12, RCA)), f'rc/{c2}': A})[0], 401)

print('--- ליגות חברים')
LID = rs(6, RCA)
check('קריאת כל הליגות (lgdef)', req('GET', 'lgdef')[0], 401)
check('פתיחת ליגה תקינה (בעלים)', req('PATCH', '', {f'lgdef/{LID}': {'n': 'pentest league', 'at': SV}, f'acct/{A}/leagues/{LID}': {'at': SV, 'own': True}})[0], 200)
check('שינוי שם של ליגה קיימת', req('PUT', f'lgdef/{LID}', {'n': 'hacked', 'at': SV})[0], 401)
check('השתלטות: B מסמן את עצמו בעלים של ליגה קיימת', req('PUT', f'acct/{B}/leagues/{LID}', {'at': SV, 'own': True})[0], 401)
check('הצטרפות תקינה של B', req('PUT', f'acct/{B}/leagues/{LID}', {'at': SV})[0], 200)
check('הצטרפות לליגה שלא קיימת', req('PUT', f'acct/{B}/leagues/{rs(6, RCA)}', {'at': SV})[0], 401)
check('הרחקה ע"י מי שאינו בעלים', req('PUT', f'acct/{B}/lgkick/{LID}/{Apid}', True)[0], 401)
check('הרחקה ע"י הבעלים', req('PUT', f'acct/{A}/lgkick/{LID}/{Bpid}', True)[0], 200)
check('זיוף טבלת ליגות (pub/lg)', req('PUT', f'pub/lg/{LID}', {'n': 'x', 'o': Bpid, 'm': {}})[0], 401)
check('עזיבת ליגה', req('DELETE', f'acct/{B}/leagues/{LID}')[0], 200)

print('--- מנהל')
check('פעולת מנהל עם מפתח מזויף', req('PUT', f'adminOps/k{rs(40, AZM)}/o1', {'t': 'adjust', 'pid': Apid, 'd': 9999, 'at': SV})[0], 401)
check('רישום מפתח מנהל חדש', req('PUT', f'adminKeys/k{rs(40, AZM)}', True)[0], 401)
check('בקשת שחזור לשם שלא קיים', req('PUT', f'recoverReq/s{rs(48, AZM)}', {'nk': 'nobody_here', 'at': SV})[0], 401)

print('--- הצפה / ניפוח המסד (DoS על המכסה החינמית)')
JUNK = 'x' * 50000
check('ליגה עם שדה זבל ענק', req('PATCH', '', {f'lgdef/{rs(6, RCA)}': {'n': 'flood', 'at': SV, 'junk': JUNK}})[0], 401)
check('בקשת שחזור עם שדה זבל ענק', req('PUT', f'recoverReq/s{rs(48, AZM)}', {'nk': Ank, 'at': SV, 'junk': JUNK})[0], 401)
check('בקשת שחזור עם nk ענק', req('PUT', f'recoverReq/s{rs(48, AZM)}', {'nk': JUNK, 'at': SV})[0], 401)
check('תפיסת שם עם מפתח ענק', req('PUT', f'names/{"y" * 300}', 'p' + rs(16, AZ))[0], 401)

print('--- המפגש השבועי (ארנק נפרד לליגת חברים)')
LID2, MID, OPEN2 = rs(6, RCA), 'm' + rs(12, AZ), '999000005'
R.fb('', 'PATCH', {f'fixtures/{OPEN2}': {'lg': 'isr1', 'home': 'Bnei Sakhnin', 'away': 'Hapoel Beer Sheva', 'ko': now + 2 * 86400000, 'day': day, 'st': 'none', 'h': 0, 'a': 0, 'odds': {'1': 2.5, 'X': 3.1, '2': 2.6}},
                   f'lgdef/{LID2}': {'n': 'pentest mt', 'at': now}, f'acct/{A}/leagues/{LID2}': {'at': now, 'own': True}, f'acct/{B}/leagues/{LID2}': {'at': now},
                   f'pub/lg/{LID2}': {'n': 'pentest mt', 'o': Apid, 'm': {Apid: 'a', Bpid: 'b'}}})   # כמו שהרובוט מפרסם
st, X, Xpid, Xnk = new_acct('pentest_x' + RUN)
mto = lambda **kw: {**{'lid': LID2, 'n': 'חמישי אצל דני', 'when': now + 86400000, 'fx': {OPEN: True}, 'at': SV}, **kw}
check('מפגש: מי שאינו בעל הליגה פותח מפגש', req('PUT', f'acct/{B}/mtown/{MID}', mto())[0], 401)
check('מפגש: פתיחה עם משחק נעול', req('PUT', f'acct/{A}/mtown/{MID}', mto(fx={OPEN: True, LOCKED: True}))[0], 401)
check('מפגש: הזרקה בשם המפגש', req('PUT', f'acct/{A}/mtown/{MID}', mto(n='x"onclick=alert(1)'))[0], 401)
check('מפגש: הזרקה/תו בלתי נראה בפרס', req('PUT', f'acct/{A}/mtown/{MID}', mto(prize='<img src=x>'))[0], 401)
check('מפגש: תו בלתי נראה בשם', req('PUT', f'acct/{A}/mtown/{MID}', mto(n='מפגש\u202e'))[0], 401)
check('מפגש: קופה מנופחת (stack) בהגדרה', req('PUT', f'acct/{A}/mtown/{MID}', mto(stack=99999))[0], 401)
check('מפגש: פרס ארוך מ-60', req('PUT', f'acct/{A}/mtown/{MID}', mto(prize='x' * 61))[0], 401)
check('מפגש: מועד בעוד שנה', req('PUT', f'acct/{A}/mtown/{MID}', mto(when=now + 365 * 86400000))[0], 401)
check('מפגש: פתיחה תקינה ע"י בעל הליגה', req('PUT', f'acct/{A}/mtown/{MID}', mto(prize='המפסיד מביא פיצה'))[0], 200)
check('מפגש: דריסת מפגש קיים', req('PUT', f'acct/{A}/mtown/{MID}', mto(n='hacked'))[0], 401)
check('מפגש: זיוף פרסום (pub/mt)', req('PUT', f'pub/mt/{LID2}/{MID}', {'st': 'open'})[0], 401)
check('מפגש: זיוף טבלת מפגש (pub/mtst)', req('PUT', f'pub/mtst/{MID}', {'rows': []})[0], 401)
check('מפגש: זיוף שיוך מפגש לליגה (pub/mtx)', req('PUT', f'pub/mtx/{MID}', LID2)[0], 401)
check('מפגש: ארנק לפני שהרובוט פרסם', req('PUT', f'acct/{B}/mt/{MID}/wallet', {'bal': 1000, 'op': 'init'})[0], 401)
R.fb('', 'PATCH', {f'pub/mtx/{MID}': LID2, f'pub/mt/{LID2}/{MID}': {'lid': LID2, 'n': 'x', 'fx': {OPEN: True}, 'st': 'open', 'stack': 1000, 'o': Apid}})
check('מפגש: מי שלא בליגה מצטרף', req('PUT', f'acct/{X}/mt/{MID}/wallet', {'bal': 1000, 'op': 'init'})[0], 401)
check('מפגש: ארנק מנופח (5,000)', req('PUT', f'acct/{B}/mt/{MID}/wallet', {'bal': 5000, 'op': 'init'})[0], 401)
check('מפגש: ארנק עם שדה נוסף', req('PUT', f'acct/{B}/mt/{MID}/wallet', {'bal': 1000, 'op': 'init', 'wk': 'x'})[0], 401)
check('מפגש: הצטרפות תקינה (1,000)', req('PUT', f'acct/{B}/mt/{MID}/wallet', {'bal': 1000, 'op': 'init'})[0], 200)
mtb = lambda sec, bid, bal, e=OPEN, s=100, o=1.8, dec=None, p='1', extra=None: {f'acct/{sec}/mt/{MID}/bets/{bid}': {'e': e, 'm': 'W', 'p': p, 's': s, 'o': o, 'at': SV, **(extra or {})},
    f'acct/{sec}/mt/{MID}/wallet/bal': bal - (s if dec is None else dec), f'acct/{sec}/mt/{MID}/wallet/op': 'b:' + bid}
check('מפגש: הימור על משחק שלא במפגש', req('PATCH', '', mtb(B, 'bmtpent01', 1000, e=OPEN2, o=2.5))[0], 401)
check('מפגש: יחס מזויף', req('PATCH', '', mtb(B, 'bmtpent02', 1000, o=9.9))[0], 401)
check('מפגש: הימור בלי להוריד מהקופה', req('PATCH', '', mtb(B, 'bmtpent03', 1000, dec=0))[0], 401)
check('מפגש: הימור מעל הקופה (1,500)', req('PATCH', '', mtb(B, 'bmtpent04', 1000, s=1500))[0], 401)
check('מפגש: ג\'וקר במפגש', req('PATCH', '', mtb(B, 'bmtpent05', 1000, extra={'j': True}))[0], 401)
check('מפגש: מי שלא בליגה מהמר', req('PATCH', '', mtb(X, 'bmtpent06', 1000))[0], 401)
check('מפגש: הימור תקין', req('PATCH', '', mtb(B, 'bmtpent07', 1000))[0], 200)
check('מפגש: איפוס הקופה ל-1,000 אחרי הימור', req('PUT', f'acct/{B}/mt/{MID}/wallet', {'bal': 1000, 'op': 'init'})[0], 401)
check('מפגש: זכייה מזויפת (settled)', req('PUT', f'acct/{B}/mt/{MID}/settled/bmtpent07', {'st': 'won', 'pay': 9999})[0], 401)
check('מפגש: שינוי סכום של הימור קיים', req('PUT', f'acct/{B}/mt/{MID}/bets/bmtpent07/s', 1)[0], 401)
check('מפגש: הימור מהקופה הראשית לתוך המפגש', req('PATCH', '', {f'acct/{B}/mt/{MID}/bets/bmtpent08': {'e': OPEN, 'm': 'W', 'p': '1', 's': 50, 'o': 1.8, 'at': SV}, f'acct/{B}/wallet/bal': 450, f'acct/{B}/wallet/op': 'b:bmtpent08'})[0], 401)
canm = lambda sec, bid, bal, s: {f'acct/{sec}/mt/{MID}/bets/{bid}': None, f'acct/{sec}/mt/{MID}/wallet/bal': bal + s, f'acct/{sec}/mt/{MID}/wallet/op': 'c:' + bid}
check('מפגש: ביטול עם החזר מנופח', req('PATCH', '', canm(B, 'bmtpent07', 900, 500))[0], 401)
check('מפגש: ביטול תקין', req('PATCH', '', canm(B, 'bmtpent07', 900, 100))[0], 200)
R.fb(f'pub/lg/{LID2}/m/{Bpid}', 'DELETE')
check('מפגש: חבר שהורחק מהליגה מהמר', req('PATCH', '', mtb(B, 'bmtpent09', 1000))[0], 401)
R.fb('', 'PATCH', {f'pub/lg/{LID2}/m/{Bpid}': 'b', f'pub/mt/{LID2}/{MID}/st': 'done'})
check('מפגש: הימור על מפגש שהסתיים', req('PATCH', '', mtb(B, 'bmtpent10', 1000))[0], 401)
check('מפגש: הצטרפות למפגש שהסתיים', req('PUT', f'acct/{A}/mt/{MID}/wallet', {'bal': 1000, 'op': 'init'})[0], 401)
sq, pq = 's' + rs(48, AZM), 'p' + rs(16, AZ)
check('חשבון חדש עם ארנק מפגש מוכן מראש', req('PATCH', '', {f'names/ptmt{RUN}': pq, f'acct/{sq}': {'name': 'ptmt' + RUN, 'nk': 'ptmt' + RUN, 'pid': pq, 'joined': SV, 'wallet': {'bal': 500, 'op': 'init'}, 'mt': {MID: {'wallet': {'bal': 99999, 'op': 'init'}}}}})[0], 401)

print('--- פידבק')
check('פידבק תקין', req('PUT', f'acct/{B}/fbk/f{rs(10, AZ)}', {'t': 'אחלה משחק! "מעולה" & תודה', 'at': SV})[0], 200)
check('פידבק ארוך מ-500', req('PUT', f'acct/{B}/fbk/f{rs(10, AZ)}', {'t': 'x' * 501, 'at': SV})[0], 401)
check('פידבק עם קוד (<script>)', req('PUT', f'acct/{B}/fbk/f{rs(10, AZ)}', {'t': '<script>alert(1)</script>', 'at': SV})[0], 401)
check('פידבק עם שדה זבל', req('PUT', f'acct/{B}/fbk/f{rs(10, AZ)}', {'t': 'hi', 'at': SV, 'junk': 'x' * 5000})[0], 401)
check('פידבק בזמן מזויף (עבר רחוק)', req('PUT', f'acct/{B}/fbk/f{rs(10, AZ)}', {'t': 'hi', 'at': 1000})[0], 401)
check('הצטרפות לליגה מחשבון שלא קיים (זבל ב-acct)', req('PUT', f'acct/s{rs(48, AZM)}/leagues/{LID2}', {'at': SV})[0], 401)
check('פידבק מחשבון שלא קיים (זבל ב-acct)', req('PUT', f'acct/s{rs(48, AZM)}/fbk/f{rs(10, AZ)}', {'t': 'hi', 'at': SV})[0], 401)
check('קריאת כל הפידבק (adminFb)', req('GET', 'adminFb')[0], 401)
check('כתיבה ישירה לפידבק של המנהל', req('PUT', f'adminFb/f{rs(10, AZ)}', {'t': 'x'})[0], 401)

st, a = req('GET', f'acct/{A}')
check('יתרה סופית של A נכונה (500−50−10 = 440)', (a or {}).get('wallet', {}).get('bal'), 440)

# ניקוי
R.fb('', 'PATCH', {f'acct/{X}': None, f'names/{Xnk}': None, f'rc/{CODES[X]}': None, f'lgdef/{LID2}': None, f'pub/lg/{LID2}': None, f'pub/mt/{LID2}': None, f'pub/mtx/{MID}': None, f'fixtures/{OPEN2}': None, f'pub/profiles/{Xpid}': None, f'acct/{G}': None, f'names/{Gnk}': None, f'rc/{CODES[G]}': None, f'pub/profiles/{Gpid}': None, f'acct/{A}': None, f'acct/{B}': None, f'names/{Ank}': None, f'names/{Bnk}': None, f'rc/{CODES[A]}': None, f'rc/{CODES[B]}': None, f'lgdef/{LID}': None,
                   f'fixtures/{OPEN}': None, f'fixtures/{LOCKED}': None, f'pub/profiles/{Apid}': None, f'pub/profiles/{Bpid}': None, f'pub/revealed/{OPEN}': None})
print(f"\nסיכום: {sum(ok for ok, _ in results)}/{len(results)} בדיקות עברו")
sys.exit(0 if all(ok for ok, _ in results) else 1)
