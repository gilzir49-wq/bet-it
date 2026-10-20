# המחזור השבועי מקצה לקצה מול סביבת הבדיקה, עם הרובוט האמיתי:
# בעל ליגה בוחר משחקים → הרובוט פותח מחזור ונותן ערימה של 1,000 לכל חבר → חברים מהמרים → משחק ננעל
# → הבית מהמר במקום מי שלא הימר (פעם אחת, לא חורג) → תוצאות → סגירה לערימת המחזור בלבד → טבלה + פודיום → טבלה עונתית.
# בנוסף: פרטיות (lgv), פידבק למנהל.
import json, time, secrets, string, urllib.request, urllib.error, sys, os, importlib.util, subprocess
DB = os.environ['DB_URL']; HERE = os.path.dirname(os.path.abspath(__file__)); ROBOT = os.path.join(HERE, '..', 'robot.py')
spec = importlib.util.spec_from_file_location('r', ROBOT); R = importlib.util.module_from_spec(spec); sys.argv = ['x']; spec.loader.exec_module(R)
def req(m, p, b=None):
    r = urllib.request.Request(f'{DB}/{p}.json', method=m, data=None if b is None else json.dumps(b).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(r, timeout=20) as x: return x.status, json.loads(x.read().decode() or 'null')
    except urllib.error.HTTPError as e: return e.code, None
rs = lambda n, a: ''.join(secrets.choice(a) for _ in range(n)); AZM = string.ascii_letters + string.digits; AZ = string.ascii_lowercase + string.digits
SV = {'.sv': 'timestamp'}; RCA = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
results = []
def check(name, cond):
    results.append((bool(cond), name)); print(('✅' if cond else '❌ FAIL'), name, flush=True)
def robot():
    out = subprocess.run([sys.executable, ROBOT, '--once'], capture_output=True, text=True, env=os.environ)
    print('   robot:', (out.stdout.strip().splitlines() or [''])[-1], out.stderr.strip()[-300:], flush=True)

now = int(time.time() * 1000); WK = R.week_key(now); END = R.week_end_ms(WK)
if END - now < 4 * 3600000:
    print('⏭️  פחות מ-4 שעות לסוף השבוע – אין מקום למשחקים "של השבוע" בבדיקה; מדלג'); sys.exit(0)
F = ['999000021', '999000022', '999000023']
odds = {'1': 2.0, 'X': 3.0, '2': 4.0, 'cs': {'2-1': 8.0}}
R.fb('', 'PATCH', {f'fixtures/{e}': {'lg': 'isr1', 'home': 'Maccabi Haifa', 'away': 'Hapoel Haifa', 'ko': now + 2 * 3600000 + i * 600000, 'day': R.day_key(now), 'st': 'none', 'h': 0, 'a': 0, 'odds': odds} for i, e in enumerate(F)})
def new_acct(name):
    sec, pid = 's' + rs(48, AZM), 'p' + rs(16, AZ)
    assert req('PATCH', '', {f'names/{name}': pid, f'acct/{sec}': {'name': name, 'nk': name, 'pid': pid, 'joined': SV, 'wallet': {'bal': 500, 'op': 'init'}}})[0] == 200
    return sec, pid
O, Opid = new_acct('rdo' + rs(6, AZ)); M1, M1pid = new_acct('rdm' + rs(6, AZ)); M2, M2pid = new_acct('rdn' + rs(6, AZ))
LID = rs(6, RCA); K = 'k' + rs(40, AZM)
P = lambda sec: f'acct/{sec}/rd/{LID}/{WK}'
def rd(sec): return ((req('GET', f'acct/{sec}')[1] or {}).get('rd') or {}).get(LID, {}).get(WK) or {}
def bet(sec, bid, e, m, p, s, o):
    bal = rd(sec)['wallet']['bal']
    return req('PATCH', '', {f'{P(sec)}/bets/{bid}': {'e': e, 'm': m, 'p': p, 's': s, 'o': o, 'at': SV}, f'{P(sec)}/wallet/bal': bal - s, f'{P(sec)}/wallet/op': 'b:' + bid})[0] == 200
autos = lambda sec: [b for b in (rd(sec).get('bets') or {}).values() if b.get('auto')]
try:
    R.fb(f'adminKeys/{K}', 'PUT', True)
    ok = req('PATCH', '', {f'lgdef/{LID}': {'n': 'rd e2e', 'at': SV}, f'acct/{O}/leagues/{LID}': {'at': SV, 'own': True}})[0] == 200
    check('ליגה: בעלים + 2 חברים', ok and req('PUT', f'acct/{M1}/leagues/{LID}', {'at': SV})[0] == 200 and req('PUT', f'acct/{M2}/leagues/{LID}', {'at': SV})[0] == 200)
    robot()
    lv = req('GET', f'lgv/{LID}')[1] or {}
    check('פרטיות: הליגה פורסמה ב-lgv עם 3 חברים; רשימת הליגות חסומה', set(lv.get('m', {})) == {Opid, M1pid, M2pid} and req('GET', 'lgv')[0] == 401)
    check('בעל הליגה בוחר 3 משחקים למחזור', req('PUT', f'acct/{O}/rdpick/{LID}/{WK}', {'fx': {e: True for e in F}, 'at': SV})[0] == 200)
    check('חבר שאינו בעלים לא בוחר', req('PUT', f'acct/{M1}/rdpick/{LID}/{WK}', {'fx': {e: True for e in F}, 'at': SV})[0] == 401)
    robot()
    r = req('GET', f'lgv/{LID}/rd/{WK}')[1] or {}
    check('הרובוט פתח את המחזור (נבחר ע"י הבעלים)', set(r.get('fx', {})) == set(F) and r.get('by') == 'owner' and r.get('st') == 'open')
    check('כל חבר קיבל ערימה של 1,000', all(rd(s).get('wallet', {}).get('bal') == 1000 for s in (O, M1, M2)))
    check('אחרי שהמחזור נפתח – אי אפשר לשנות בחירה', req('PUT', f'acct/{O}/rdpick/{LID}/{WK}', {'fx': {F[0]: True}, 'at': SV})[0] == 401)
    check('הימורים: חבר 1 על משחק 1+2, חבר 2 על משחק 1, הבעלים על כלום',
          bet(M1, 'brde2e0001', F[0], 'W', '1', 300, 2.0) and bet(M1, 'brde2e0002', F[1], 'CS', '2-1', 200, 8.0) and bet(M2, 'brde2e0003', F[0], 'W', 'X', 500, 3.0))
    check('ניסיון לזייף הימור אוטומטי מהלקוח', req('PATCH', '', {f'{P(O)}/bets/brde2e0009': {'e': F[0], 'm': 'W', 'p': '1', 's': 10, 'o': 2.0, 'at': SV, 'auto': True}, f'{P(O)}/wallet/bal': 990, f'{P(O)}/wallet/op': 'b:brde2e0009'})[0] == 401)
    # משחק 1 ננעל (2 דקות לפני הפתיחה + 30 שניות חסד)
    R.fb(f'fixtures/{F[0]}/ko', 'PUT', R.now_ms() + 60000)
    robot()
    ao = autos(O)
    check('הבית הימר במקום הבעלים על משחק 1 (רק שם)', len(ao) == 1 and ao[0]['e'] == F[0] and ao[0]['p'] in ('1', 'X', '2'))
    check('…סכום 1000/3 = 333, יורד מהערימה', ao and ao[0]['s'] == 333 and rd(O)['wallet']['bal'] == 667)
    check('מי שהימר בעצמו – לא קיבל הימור אוטומטי', not autos(M1) and not autos(M2))
    robot()
    check('הימור אוטומטי לא נוצר פעמיים', len(autos(O)) == 1)
    lt = req('GET', f'lgv/{LID}/rdst/{WK}')[1] or {}
    check('טבלת מחזור לייב פורסמה (3 שורות, st=live)', len(lt.get('rows', [])) == 3 and lt.get('st') == 'live')
    # משחקים 2+3 ננעלים
    R.fb('', 'PATCH', {f'fixtures/{F[1]}/ko': R.now_ms() + 60000, f'fixtures/{F[2]}/ko': R.now_ms() + 60000})
    robot()
    bo, b1, b2 = rd(O), rd(M1), rd(M2)
    check('הבית השלים: לבעלים 3 אוטומטיים, לחבר 1 אחד (משחק 3), לחבר 2 שניים', len(autos(O)) == 3 and len(autos(M1)) == 1 and len(autos(M2)) == 2)
    check('אף ערימה לא ירדה מתחת ל-0', all(x['wallet']['bal'] >= 0 for x in (bo, b1, b2)))
    check('לכל חבר הימור על כל משחקי המחזור', all({b['e'] for b in x['bets'].values()} == set(F) for x in (bo, b1, b2)))
    check('פידבק מחבר', req('PUT', f'acct/{M1}/fbk/f{rs(10, AZ)}', {'t': 'מחזור מעולה! תוסיפו התראה לפני נעילה', 'at': SV})[0] == 200)
    # תוצאות: 2-0, 2-1, 0-1
    R.fb('', 'PATCH', {f'fixtures/{F[0]}/st': 'finished', f'fixtures/{F[0]}/h': 2, f'fixtures/{F[1]}/st': 'finished', f'fixtures/{F[1]}/h': 2, f'fixtures/{F[1]}/a': 1,
                       f'fixtures/{F[2]}/st': 'finished', f'fixtures/{F[2]}/a': 1})
    robot()
    res = {1: (2, 0), 2: (2, 1), 3: (0, 1)}
    def expect(x):
        tot = x['wallet']['bal']; sett = 0
        for b in x['bets'].values():
            h, a = res[F.index(b['e']) + 1]
            w = (f'{h}-{a}' == b['p']) if b['m'] == 'CS' else ({'1': 1, 'X': 0, '2': -1}[b['p']] == (h > a) - (h < a))
            sett += R.payout(b) if w else 0
        return tot + sett
    exp = {s: expect(x) for s, x in ((O, bo), (M1, b1), (M2, b2))}
    got = {s: rd(s)['wallet']['bal'] for s in (O, M1, M2)}
    check(f'סגירה לתוך ערימת המחזור (צפוי {list(exp.values())})', got == exp)
    mains = [req('GET', f'acct/{s}')[1] for s in (O, M1, M2)]
    check('היתרה הראשית לא השתנתה (500) ואין בה סגירות', all(a['wallet']['bal'] == 500 and not a.get('settled') for a in mains))
    st = req('GET', f'lgv/{LID}/rdst/{WK}')[1] or {}
    order = sorted(exp, key=lambda s: -exp[s]); pid = {O: Opid, M1: M1pid, M2: M2pid}
    check('המחזור הסתיים + פודיום לפי הערימות', st.get('st') == 'done' and st.get('podium') and st['podium'][0]['pid'] == pid[order[0]])
    check('הימורים אוטומטיים מסומנים בטבלה', any(b.get('a') for r_ in st.get('rows', []) for b in r_.get('b', [])))
    sm = {x['pid']: x for x in (req('GET', f'lgv/{LID}/rdsum')[1] or {}).get('rows', [])}
    check('טבלה עונתית: 10 / 7 / 5 נקודות לפי מקום', sorted(x['pts'] for x in sm.values()) == sorted(R.RD_POINTS.get(r_['rk'], 2) for r_ in st['rows']) and sm[pid[order[0]]]['pts'] == 10)
    fbv = R.fb(f'adminView/{K}/fb') or {}
    check('פידבק הגיע למסך המנהל ונמחק מהחשבון', any('התראה' in (x.get('t') or '') and x.get('pid') == M1pid for x in fbv.values()) and not req('GET', f'acct/{M1}/fbk')[1])
finally:
    upd = {f'acct/{s}': None for s in (O, M1, M2)}
    upd.update({f'lgdef/{LID}': None, f'lgv/{LID}': None, f'pub/lg/{LID}': None, f'adminView/{K}': None})
    for e in F: upd[f'fixtures/{e}'] = None
    for p_ in (Opid, M1pid, M2pid): upd[f'pub/profiles/{p_}'] = None
    for nk, p_ in (R.fb('names') or {}).items():
        if p_ in (Opid, M1pid, M2pid): upd[f'names/{nk}'] = None
    for fid, x in (R.fb('adminFb') or {}).items():
        if x.get('pid') in (Opid, M1pid, M2pid): upd[f'adminFb/{fid}'] = None
    R.fb('', 'PATCH', upd); R.fb(f'adminKeys/{K}', 'DELETE')
print(f"\nסיכום: {sum(ok for ok, _ in results)}/{len(results)} בדיקות עברו")
sys.exit(0 if all(ok for ok, _ in results) else 1)
