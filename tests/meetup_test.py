# המפגש השבועי מקצה לקצה מול סביבת הבדיקה, עם הרובוט האמיתי:
# בעל ליגה פותח מפגש → 2 חברים מצטרפים ומהמרים → המשחקים נגמרים → הרובוט סוגר לתוך ארנקי המפגש בלבד
# → טבלת מפגש + פודיום → טבלה מצטברת לליגה. בנוסף: פידבק עובר למסך המנהל.
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

now = int(time.time() * 1000); day = R.day_key(now + 86400000)
F = ['999000011', '999000012', '999000013']
odds = {'1': 2.0, 'X': 3.0, '2': 4.0, 'cs': {'2-1': 8.0}}
R.fb('', 'PATCH', {f'fixtures/{e}': {'lg': 'isr1', 'home': 'Maccabi Haifa', 'away': 'Hapoel Haifa', 'ko': now + 86400000 + i * 3600000, 'day': day, 'st': 'none', 'h': 0, 'a': 0, 'odds': odds} for i, e in enumerate(F)})
def new_acct(name):
    sec, pid = 's' + rs(48, AZM), 'p' + rs(16, AZ)
    assert req('PATCH', '', {f'names/{name}': pid, f'acct/{sec}': {'name': name, 'nk': name, 'pid': pid, 'joined': SV, 'wallet': {'bal': 500, 'op': 'init'}}})[0] == 200
    return sec, pid
O, Opid = new_acct('mto' + rs(6, AZ)); M, Mpid = new_acct('mtm' + rs(6, AZ))
LID = rs(6, RCA); MID1, MID2, MID3 = 'm' + rs(12, AZ), 'm' + rs(12, AZ), 'm' + rs(12, AZ)
K = 'k' + rs(40, AZM)
try:
    R.fb(f'adminKeys/{K}', 'PUT', True)
    check('בעל הליגה פותח ליגה וחבר מצטרף', req('PATCH', '', {f'lgdef/{LID}': {'n': 'mt e2e', 'at': SV}, f'acct/{O}/leagues/{LID}': {'at': SV, 'own': True}})[0] == 200
          and req('PUT', f'acct/{M}/leagues/{LID}', {'at': SV})[0] == 200)
    mt = lambda fx, n: {'lid': LID, 'n': n, 'when': now + 86400000, 'fx': {e: True for e in fx}, 'prize': 'המפסיד מביא פיצה', 'at': SV}
    check('בעל הליגה פותח 2 מפגשים (3 משחקים כל אחד)', req('PUT', f'acct/{O}/mtown/{MID1}', mt(F, 'חמישי אצל דני'))[0] == 200 and req('PUT', f'acct/{O}/mtown/{MID2}', mt(F, 'שבת'))[0] == 200)
    check('מפגש עם 2 משחקים בלבד נכתב (החוקים) …', req('PUT', f'acct/{O}/mtown/{MID3}', mt(F[:2], 'קטן מדי'))[0] == 200)
    check('חבר שאינו בעלים לא יכול לפתוח מפגש', req('PUT', f'acct/{M}/mtown/m{rs(12, AZ)}', mt(F, 'x'))[0] == 401)
    robot()
    pm = req('GET', f'pub/mt/{LID}')[1] or {}
    check('הרובוט פרסם את המפגשים התקינים', MID1 in pm and MID2 in pm and pm[MID1]['st'] == 'open' and pm[MID1]['stack'] == 1000 and pm[MID1]['o'] == Opid)
    check('… ולא פרסם מפגש עם פחות מ-3 משחקים', MID3 not in pm)
    def join(sec, mid): return req('PUT', f'acct/{sec}/mt/{mid}/wallet', {'bal': 1000, 'op': 'init'})[0] == 200
    bal = {}
    def bet(sec, mid, bid, e, m, p, s, o):
        k = (sec, mid); b0 = bal.get(k, 1000)
        st = req('PATCH', '', {f'acct/{sec}/mt/{mid}/bets/{bid}': {'e': e, 'm': m, 'p': p, 's': s, 'o': o, 'at': SV}, f'acct/{sec}/mt/{mid}/wallet/bal': b0 - s, f'acct/{sec}/mt/{mid}/wallet/op': 'b:' + bid})[0]
        if st == 200: bal[k] = b0 - s
        return st == 200
    check('שני החברים מצטרפים למפגש 1 (1,000 כל אחד)', join(O, MID1) and join(M, MID1))
    ok = bet(O, MID1, 'bmte2e0001', F[0], 'W', '1', 300, 2.0) and bet(O, MID1, 'bmte2e0002', F[1], 'CS', '2-1', 200, 8.0)
    ok = ok and bet(M, MID1, 'bmte2e0003', F[0], 'W', 'X', 500, 3.0) and bet(M, MID1, 'bmte2e0004', F[2], 'W', '2', 100, 4.0)
    check('הימורים במפגש 1', ok)
    check('במפגש 2 רק החבר משתתף', join(M, MID2) and bet(M, MID2, 'bmte2e0005', F[2], 'W', '2', 1000, 4.0))
    check('פידבק מהחבר', req('PUT', f'acct/{M}/fbk/f{rs(10, AZ)}', {'t': 'מפגש מעולה! תוסיפו צ׳אט', 'at': SV})[0] == 200)
    # המשחקים נגמרים: 2-0, 2-1, 0-1
    R.fb('', 'PATCH', {f'fixtures/{F[0]}/st': 'finished', f'fixtures/{F[0]}/h': 2, f'fixtures/{F[0]}/ko': now - 7200000,
                       f'fixtures/{F[1]}/st': 'finished', f'fixtures/{F[1]}/h': 2, f'fixtures/{F[1]}/a': 1, f'fixtures/{F[1]}/ko': now - 7200000,
                       f'fixtures/{F[2]}/st': 'finished', f'fixtures/{F[2]}/a': 1, f'fixtures/{F[2]}/ko': now - 7200000})
    robot()
    o, m = req('GET', f'acct/{O}')[1], req('GET', f'acct/{M}')[1]
    # O: 1000-300-200 + 600 + 1600 = 2700 · M: 1000-500-100 + 400 = 800 · M במפגש 2: 0 + 4000 = 4000
    check('סגירה לתוך ארנק המפגש: בעל הליגה 2,700', o['mt'][MID1]['wallet']['bal'] == 2700)
    check('סגירה לתוך ארנק המפגש: החבר 800', m['mt'][MID1]['wallet']['bal'] == 800 and m['mt'][MID2]['wallet']['bal'] == 4000)
    check('היתרה הראשית לא השתנתה (500) ואין סגירות בה', o['wallet']['bal'] == 500 and m['wallet']['bal'] == 500 and not o.get('settled') and not m.get('settled'))
    s1 = req('GET', f'pub/mtst/{MID1}')[1] or {}
    rows = {r['pid']: r for r in s1.get('rows', [])}
    check('טבלת המפגש: מקום 1 בעל הליגה (2,700), מקום 2 החבר (800)', rows.get(Opid, {}).get('rk') == 1 and rows[Opid]['v'] == 2700 and rows.get(Mpid, {}).get('rk') == 2 and rows[Mpid]['v'] == 800)
    check('המפגש הסתיים + פודיום', s1.get('st') == 'done' and [p['pid'] for p in s1.get('podium', [])] == [Opid, Mpid])
    check('ההימורים נחשפים בטבלת המפגש אחרי הנעילה', len(rows[Mpid].get('b') or []) == 2)
    check('pub/mt מסומן "הסתיים"', (req('GET', f'pub/mt/{LID}/{MID1}/st')[1]) == 'done')
    sm = {r['pid']: r for r in (req('GET', f'pub/mtsum/{LID}')[1] or {}).get('rows', [])}
    check('טבלה מצטברת: החבר 17 נק׳ (7+10) מקום 1, בעל הליגה 10 נק׳', sm.get(Mpid, {}).get('pts') == 17 and sm[Mpid]['rk'] == 1 and sm.get(Opid, {}).get('pts') == 10 and sm[Opid]['mts'] == 1)
    fbv = R.fb(f'adminView/{K}/fb') or {}
    check('הפידבק עבר למסך המנהל ונמחק מהחשבון', any('צ׳אט' in (x.get('t') or '') and x.get('pid') == Mpid for x in fbv.values()) and not (req('GET', f'acct/{M}/fbk')[1]))
finally:
    upd = {f'acct/{O}': None, f'acct/{M}': None, f'lgdef/{LID}': None, f'pub/lg/{LID}': None, f'pub/mt/{LID}': None, f'pub/mtsum/{LID}': None, f'adminView/{K}': None}
    for mid in (MID1, MID2, MID3): upd.update({f'pub/mtst/{mid}': None, f'pub/mtx/{mid}': None})
    for e in F: upd[f'fixtures/{e}'] = None
    for s_, p_ in ((O, Opid), (M, Mpid)): upd[f'pub/profiles/{p_}'] = None
    for nk, pid in (R.fb('names') or {}).items():
        if pid in (Opid, Mpid): upd[f'names/{nk}'] = None
    fl = R.fb('adminFb') or {}
    for fid, x in fl.items():
        if x.get('pid') in (Opid, Mpid): upd[f'adminFb/{fid}'] = None
    R.fb('', 'PATCH', upd); R.fb(f'adminKeys/{K}', 'DELETE')
print(f"\nסיכום: {sum(ok for ok, _ in results)}/{len(results)} בדיקות עברו")
sys.exit(0 if all(ok for ok, _ in results) else 1)
