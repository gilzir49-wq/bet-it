# רובוט BUX BET – "הבנק" המוסמך היחיד.
# מביא משחקים (היום + 3 ימים) מ-4 ליגות, יחסים, תוצאות לייב וטבלאות; סוגר הימורים ומשלם זכיות;
# מחלק מענק שבועי; מפרסם טבלאות דירוג, קופת בנק והימורים שנחשפו; מבצע פעולות מנהל.
# כותב ל-Firebase עם מפתח שירות (נשמר בכספת של GitHub, לא בקוד).
import json, time, math, os, sys, datetime, hashlib, urllib.request, urllib.error
from zoneinfo import ZoneInfo
from google.oauth2 import service_account
from google.auth.transport.requests import Request

DB = os.environ.get('DB_URL', 'https://buxbet-il-default-rtdb.europe-west1.firebasedatabase.app')
IL = ZoneInfo('Asia/Jerusalem')
LS = 'https://prod-public-api.livescore.com/v1/api/app'
LEAGUES = {'isr1': ('israel', 'premier-league'), 'isr2': ('israel', 'liga-leumit'),
           'eng': ('england', 'premier-league'), 'ita': ('italy', 'serie-a')}
DAYS_AHEAD = 7   # משחקים לשבוע קדימה
REFRESH_EVERY = 600
POLL = 20
RUN_FOR = 5 * 3600 + 40 * 60
MARGIN = 1.07
START, WEEKLY, BANK_START = 500, 50, 10000
LOCK_MS = 120000

# ---------- הרשאות ----------
_info = json.loads(os.environ['FIREBASE_SA']) if os.environ.get('FIREBASE_SA') else json.load(open(os.path.expanduser('~/.config/buxbet/sa.json')))
_creds = service_account.Credentials.from_service_account_info(_info, scopes=[
    'https://www.googleapis.com/auth/firebase.database', 'https://www.googleapis.com/auth/userinfo.email'])
def tok():
    if not _creds.valid: _creds.refresh(Request())
    return _creds.token

def fb(path, method='GET', body=None, etag=False, if_match=None):
    h = {'Authorization': 'Bearer ' + tok(), 'Content-Type': 'application/json'}
    if etag: h['X-Firebase-ETag'] = 'true'
    if if_match: h['if-match'] = if_match
    req = urllib.request.Request(f'{DB}/{path}.json', method=method, headers=h,
                                 data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode() or 'null')
            return (data, r.headers.get('ETag')) if etag else data
    except urllib.error.HTTPError as e:
        if e.code == 412: return 'CONFLICT'
        raise

def ls(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read().decode())

# ---------- זמן ----------
now_ms = lambda: int(time.time() * 1000)
def day_key(ms): return datetime.datetime.fromtimestamp(ms / 1000, IL).strftime('%Y-%m-%d')
def week_key(ms):
    d = datetime.datetime.fromtimestamp(ms / 1000, IL).date()
    return (d - datetime.timedelta(days=(d.weekday() - 1) % 7)).isoformat()   # שבוע: שלישי → שני
def esd_ms(esd):
    s = str(esd)
    return int(datetime.datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]), int(s[8:10]), int(s[10:12]),
                                 tzinfo=datetime.timezone.utc).timestamp() * 1000)
def status_of(eps):
    eps = (eps or '').strip()
    if eps in ('FT', 'AET', 'AP', 'Ended'): return 'finished'
    if eps in ('Postp.', 'Canc.', 'Abd.', 'Susp.'): return 'postp'
    if eps in ('NS', '', 'TBA', 'Delayed'): return 'none'
    return 'live'

# ---------- יחסים (פואסון) ----------
def poisson(k, lam): return math.exp(-lam) * lam ** k / math.factorial(k)
def calc_odds(table, home, away):
    rows = {r['t']: r for r in table}; tp = sum(r['pld'] for r in table) or 1
    mu = max(0.6, sum(r['gf'] for r in table) / tp)
    def st(t, k):
        r = rows.get(t)
        if not r or not r['pld']: return 1.0
        w = r['pld'] / (r['pld'] + 5); return 1 + ((r[k] / r['pld']) / mu - 1) * w
    lh = max(0.25, mu * st(home, 'gf') * st(away, 'ga') * 1.12); la = max(0.2, mu * st(away, 'gf') * st(home, 'ga') * 0.9)
    p1 = px = p2 = 0.0; cs = {}
    for i in range(9):
        for j in range(9):
            p = poisson(i, lh) * poisson(j, la)
            if i > j: p1 += p
            elif i == j: px += p
            else: p2 += p
            if i <= 4 and j <= 4: cs[f'{i}-{j}'] = p
    o = lambda p, lo=1.05, hi=15: round(min(hi, max(lo, 1 / (p * MARGIN))), 2)
    return {'1': o(p1), 'X': o(px), '2': o(p2), 'cs': {k: o(p, 3.0, 80) for k, p in cs.items()}, 'lam': {'h': round(lh, 3), 'a': round(la, 3)}}

# ---------- מצב ----------
fixtures, tables = {}, {}
published = {}          # מה שכבר פורסם (כדי לא לכתוב שוב בלי שינוי)
last_ranks = {}         # לחצים בטבלה
orphan_seen = {}

def table_rows(st):
    lt = st.get('LeagueTable')
    if not lt: return []
    imgs = {}
    for e in st.get('Events', []):
        for T in ('T1', 'T2'):
            if e[T][0].get('Img'): imgs[e[T][0]['Nm']] = e[T][0]['Img']
    return [{'t': r['Tnm'], 'img': r.get('Img') or imgs.get(r['Tnm'], ''), 'pld': r['pld'], 'w': r['win'], 'd': r['drw'],
             'l': r['lst'], 'gf': r['gf'], 'ga': r['ga'], 'pts': r['pts']} for r in lt['L'][0]['Tables'][0]['team']]

def pld_of(lg, team):
    for r in tables.get(lg, []):
        if r['t'] == team: return r['pld']

def refresh():
    now = now_ms()
    today = datetime.datetime.now(IL).replace(hour=0, minute=0, second=0, microsecond=0)
    lo, hi = today.timestamp() * 1000, (today + datetime.timedelta(days=DAYS_AHEAD + 1)).timestamp() * 1000
    upd = {}
    for lg, (c, s) in LEAGUES.items():
        try: st = ls(f'{LS}/stage/soccer/{c}/{s}/0?MD=1')['Stages'][0]
        except Exception as ex: print('stage error', lg, ex, flush=True); continue
        rows = table_rows(st)
        if rows: tables[lg] = rows; upd[f'pub/tables/{lg}'] = {'rows': rows, 'at': now}
        for e in st.get('Events', []):
            eid = str(e['Eid']); ko = esd_ms(e['Esd']); f = fixtures.get(eid)
            if not f and not (lo <= ko < hi): continue
            nf = dict(f or {})
            nf.update({'lg': lg, 'home': e['T1'][0]['Nm'], 'away': e['T2'][0]['Nm'], 'hi': e['T1'][0].get('Img') or '',
                       'ai': e['T2'][0].get('Img') or '', 'ko': ko, 'day': day_key(ko)})
            stt = status_of(e.get('Eps'))
            if not f:
                nf.update({'st': stt, 'h': int(e.get('Tr1') or 0), 'a': int(e.get('Tr2') or 0)})
                if stt == 'finished': nf['inT'] = True
            elif not nf.get('manual'):
                if stt == 'postp': nf['st'] = 'postp'
                elif nf.get('st') == 'postp' and stt == 'none': nf['st'] = 'none'
            if nf.get('st') == 'none' and ko - now > LOCK_MS and rows:
                od = calc_odds(rows, nf['home'], nf['away']); nf['lam'] = od.pop('lam'); nf['odds'] = od   # lam = צפי שערים (לסיכוי זכייה לייב)
            if nf.get('st') == 'finished' and not nf.get('inT') and nf.get('bh') is not None:
                p = pld_of(lg, nf['home'])
                if p is not None and p > nf['bh']: nf['inT'] = True
            if nf != f: fixtures[eid] = nf; upd[f'fixtures/{eid}'] = nf
    if upd: fb('', 'PATCH', upd)
    return sum(1 for k in upd if k.startswith('fixtures/'))

def live_tick():
    now = now_ms()
    need = [e for e, f in fixtures.items() if not f.get('manual') and f.get('st') in ('none', 'live')
            and f['ko'] <= now + 60000 and f['ko'] > now - 5 * 3600 * 1000]
    if not need: return {}
    ev = {}
    for dd in sorted({datetime.datetime.fromtimestamp(fixtures[e]['ko'] / 1000, datetime.timezone.utc).strftime('%Y%m%d') for e in need}):
        for s in ls(f'{LS}/date/soccer/{dd}/0?MD=1').get('Stages', []):
            for e in s.get('Events', []): ev[str(e['Eid'])] = e
    upd, prev = {}, {}
    for eid in need:
        e = ev.get(eid)
        if not e: continue
        f = fixtures[eid]; st = status_of(e.get('Eps'))
        h = int(e.get('Tr1') or 0) if st in ('live', 'finished') else 0
        a = int(e.get('Tr2') or 0) if st in ('live', 'finished') else 0
        nf = dict(f)
        if st == 'live' and f.get('bh') is None: nf['bh'] = pld_of(f['lg'], f['home']); nf['ba'] = pld_of(f['lg'], f['away'])
        if (h, a, st) != (f.get('h'), f.get('a'), f.get('st')): prev[eid] = {'h': f.get('h', 0), 'a': f.get('a', 0), 'st': f.get('st')}
        nf.update({'st': st, 'h': h, 'a': a})
        if st == 'live': nf['min'] = (e.get('Eps') or '').strip()
        else: nf.pop('min', None)
        if st == 'finished' and nf.get('odds'): nf['odds'] = {k: v for k, v in nf['odds'].items() if k != 'cs'}
        if nf != f: fixtures[eid] = nf; upd[f'fixtures/{eid}'] = nf
    if upd: fb('', 'PATCH', upd)
    return prev

# ---------- הימורים: מצב, תשלום ----------
sign = lambda n: (n > 0) - (n < 0)
def wins(f, b):
    if b['m'] == 'CS': return f"{f['h']}-{f['a']}" == b['p']
    return {'1': 1, 'X': 0, '2': -1}[b['p']] == sign(f['h'] - f['a'])
def payout(b): return round(b['s'] + 2 * (b['s'] * b['o'] - b['s'])) if b.get('j') else round(b['s'] * b['o'])
def state(b, F=None):
    f = (F or fixtures).get(b['e'])
    if not f: return 'open'
    if f['st'] == 'postp': return 'void'
    if f['st'] == 'finished': return 'won' if wins(f, b) else 'lost'
    if f['st'] == 'live': return 'live-win' if wins(f, b) else 'live-lose'
    return 'open'

def settle_account(sec):
    """סגירת הימורים + מענק שבועי לחשבון אחד – בפעולה אטומית (ETag)."""
    for _ in range(5):
        acct, et = fb(f'acct/{sec}', etag=True)
        if not acct: return 0
        w = acct.setdefault('wallet', {'bal': 0}); settled = acct.setdefault('settled', {}); changed = 0
        for bid, b in (acct.get('bets') or {}).items():
            if bid in settled: continue
            st = state(b)
            if st in ('won', 'lost', 'void'):
                pay = payout(b) if st == 'won' else (b['s'] if st == 'void' else 0)
                settled[bid] = {'st': st, 'pay': pay, 'at': now_ms()}
                w['bal'] = w.get('bal', 0) + pay; w['op'] = 's:' + bid; changed += 1
        wk = week_key(now_ms())
        if w.get('wk') != wk:
            if week_key(acct.get('joined', 0)) != wk:            # מי שהצטרף השבוע כבר קיבל 500
                w['bal'] = w.get('bal', 0) + WEEKLY; w['bn'] = w.get('bn', 0) + WEEKLY; w['op'] = 'w:' + wk
            w['wk'] = wk; changed += 1
        if not changed: return 0
        if fb(f'acct/{sec}', 'PUT', acct, if_match=et) != 'CONFLICT': return changed
        time.sleep(0.5)
    return 0

def needs_settle(acct):
    w = acct.get('wallet') or {}; settled = acct.get('settled') or {}
    if w.get('wk') != week_key(now_ms()): return True
    return any(bid not in settled and state(b) in ('won', 'lost', 'void') for bid, b in (acct.get('bets') or {}).items())

# ---------- פרסום: טבלאות, בנק, הימורים שנחשפו ----------
def calc(a, F):
    """שווי חי, רווח שבועי וסטטיסטיקה לחשבון (כולל משחקים שרצים עכשיו)."""
    wk = week_key(now_ms()); w = a.get('wallet') or {}; bal = w.get('bal', 0); settled = a.get('settled') or {}
    value, wkp, won, done, nwk = bal, 0, 0, 0, 0
    for bid, b in (a.get('bets') or {}).items():
        f = F.get(b['e']); s = settled.get(bid)
        st = s['st'] if s else {'live-win': 'won', 'live-lose': 'lost'}.get(state(b, F), state(b, F))
        v = payout(b) if st == 'won' else (b['s'] if st in ('void', 'open') else 0)
        if not s: value += v
        if st in ('won', 'lost'):
            if s or (f and f['st'] == 'finished'): done += 1; won += st == 'won'
        if f and week_key(f['ko']) == wk:
            nwk += 1
            if st in ('won', 'lost'): wkp += v - b['s']
    return value, wkp, won, done, nwk

def ranks(key, rs):
    srt = sorted(rs, key=lambda r: (-r[key], -r['won'], r['n'])); out, prev = {}, None
    for i, r in enumerate(srt):
        out[r['pid']] = out[prev['pid']] if prev and prev[key] == r[key] else i + 1; prev = r
    return out

def publish(accts, prev_fx):
    now = now_ms(); wk = week_key(now)
    rows, bank, revealed, profiles = [], BANK_START, {}, {}
    for sec, a in accts.items():
        if not a or 'pid' not in a: continue
        value, wkp, won, done, nwk = calc(a, fixtures)
        rows.append({'pid': a['pid'], 'n': a['name'], 'v': round(value), 'wp': round(wkp), 'won': won, 'dn': done, 'nw': nwk,
                     'nb': len(a.get('bets') or {})})
        profiles[a['pid']] = {'n': a['name'], 'j': a.get('joined', 0)}
        bank -= (a.get('wallet') or {}).get('bn', 0)
        settled = a.get('settled') or {}
        for bid, b in (a.get('bets') or {}).items():
            f = fixtures.get(b['e']); s = settled.get(bid); st = s['st'] if s else state(b)
            if st in ('lost', 'live-lose'): bank += b['s']
            elif st in ('won', 'live-win'): bank -= payout(b) - b['s']
            if f and (f['st'] != 'none' or now >= f['ko'] - LOCK_MS):           # נחשף רק אחרי הנעילה
                revealed.setdefault(b['e'], {})[f"{a['pid']}_{bid}"] = {'n': a['name'], 'm': b['m'], 'p': b['p'], 's': b['s'], 'j': bool(b.get('j')), 'st': st}
    rw, rs = ranks('wp', rows), ranks('v', rows)
    if prev_fx:   # חצים: הדירוג לפני השינוי האחרון בתוצאות
        F0 = dict(fixtures); F0.update({e: {**fixtures[e], **v} for e, v in prev_fx.items() if e in fixtures})
        old = []
        for a in accts.values():
            if a and 'pid' in a:
                value, wkp, won, done, nwk = calc(a, F0); old.append({'pid': a['pid'], 'n': a['name'], 'v': value, 'wp': wkp, 'won': won})
        last_ranks.update({'w': ranks('wp', old), 's': ranks('v', old)})
    for r in rows:
        r['rw'], r['rs'] = rw[r['pid']], rs[r['pid']]
        r['pw'] = last_ranks.get('w', {}).get(r['pid'], r['rw']); r['ps'] = last_ranks.get('s', {}).get(r['pid'], r['rs'])
    st_body = {'rows': rows, 'wk': wk, 'bank': round(bank)}
    upd = {}
    if published.get('standings') != json.dumps(st_body, sort_keys=True): upd['pub/standings'] = {**st_body, 'at': now}
    if published.get('profiles') != json.dumps(profiles, sort_keys=True): upd['pub/profiles'] = profiles
    for e, v in revealed.items():
        if published.get('rv' + e) != json.dumps(v, sort_keys=True): upd[f'pub/revealed/{e}'] = v
    if upd:
        fb('', 'PATCH', upd)
        published['standings'] = json.dumps(st_body, sort_keys=True); published['profiles'] = json.dumps(profiles, sort_keys=True)
        for e, v in revealed.items(): published['rv' + e] = json.dumps(v, sort_keys=True)

# ---------- מנהל ----------
rid = lambda s: hashlib.sha256(s.encode()).hexdigest()[:10]
def admin_tick(accts):
    keys = fb('adminKeys') or {}
    if not keys: return
    reqs = fb('recoverReq') or {}
    by_nk = {a.get('nk'): (s, a) for s, a in accts.items() if a}
    users = [{'pid': a['pid'], 'n': a['name'], 'bal': (a.get('wallet') or {}).get('bal', 0), 'nb': len(a.get('bets') or {}),
              'j': a.get('joined', 0)} for a in accts.values() if a and 'pid' in a]
    rq = [{'rid': rid(s), 'nk': r.get('nk'), 'n': (by_nk.get(r.get('nk'), (None, {}))[1] or {}).get('name', r.get('nk')), 'at': r.get('at', 0)}
          for s, r in reqs.items() if r]
    for k in keys:
        ops = fb(f'adminOps/{k}') or {}
        for oid, op in sorted(ops.items(), key=lambda x: x[1].get('at', 0)):
            t = op.get('t'); res = 'ok'
            try:
                if t in ('approve', 'reject'):
                    s2 = next((s for s in reqs if rid(s) == op.get('rid')), None)
                    if not s2: res = 'not found'
                    elif t == 'approve':
                        old = by_nk.get(reqs[s2].get('nk'))
                        if not old: res = 'not found'
                        else: fb(f'acct/{s2}', 'PUT', old[1]); fb(f'acct/{old[0]}', 'DELETE'); fb(f'recoverReq/{s2}', 'DELETE')
                    else: fb(f'recoverReq/{s2}', 'DELETE')
                elif t == 'delete':
                    hit = next(((s, a) for s, a in accts.items() if a and a.get('pid') == op.get('pid')), None)
                    if hit: fb('', 'PATCH', {f'acct/{hit[0]}': None, f"names/{hit[1]['nk']}": None, f"pub/profiles/{hit[1]['pid']}": None})
                    else: res = 'not found'
                elif t == 'adjust':
                    hit = next((s for s, a in accts.items() if a and a.get('pid') == op.get('pid')), None)
                    if not hit: res = 'not found'
                    for _ in range(5 if hit else 0):
                        w, et = fb(f'acct/{hit}/wallet', etag=True); w = w or {'bal': 0}
                        w['bal'] = max(0, w.get('bal', 0) + int(op.get('d', 0))); w['op'] = 'a:' + oid
                        if fb(f'acct/{hit}/wallet', 'PUT', w, if_match=et) != 'CONFLICT': break
                elif t == 'fix':
                    e = str(op.get('e')); f = fixtures.get(e)
                    if not f: res = 'not found'
                    else:
                        nf = {**f, 'h': int(op.get('h', 0)), 'a': int(op.get('a', 0)), 'st': op.get('st', 'finished'), 'manual': True}
                        fixtures[e] = nf; fb(f'fixtures/{e}', 'PUT', nf)
                elif t == 'unfix':
                    e = str(op.get('e')); f = fixtures.get(e)
                    if f: f.pop('manual', None); fb(f'fixtures/{e}', 'PUT', f)
                else: res = 'unknown'
            except Exception as ex: res = f'error {ex}'
            fb(f'adminOps/{k}/{oid}', 'DELETE'); fb(f'adminView/{k}/log/{oid}', 'PUT', {'t': t, 'res': res, 'at': now_ms()})
            print('admin op', t, res, flush=True)
        sig = json.dumps([users, rq], sort_keys=True)
        if published.get('av' + k) != sig:
            fb(f'adminView/{k}', 'PATCH', {'users': users, 'reqs': rq}); published['av' + k] = sig
        fb(f'adminView/{k}/robot', 'PUT', now_ms())

def cleanup_names(accts):
    """שמות שנתפסו בלי חשבון (ספאם) – נמחקים אחרי 3 דקות."""
    names = fb('names') or {}; pids = {a.get('pid') for a in accts.values() if a}; t = time.time()
    for nk, pid in names.items():
        if pid in pids: orphan_seen.pop(nk, None); continue
        if t - orphan_seen.setdefault(nk, t) > 180: fb(f'names/{nk}', 'DELETE'); orphan_seen.pop(nk, None)

# ---------- לולאה ----------
if __name__ == '__main__':
    once = '--once' in sys.argv; started = time.time()
    fixtures.update(fb('fixtures') or {})
    for lg, v in (fb('pub/tables') or {}).items(): tables[lg] = v.get('rows', [])
    last_refresh = 0
    while True:
        try:
            msg = []
            if time.time() - last_refresh > REFRESH_EVERY: msg.append(f'refresh {refresh()}'); last_refresh = time.time()
            prev = live_tick()
            if prev: msg.append(f'live changes {list(prev)}')
            accts = fb('acct') or {}
            n = sum(settle_account(s) for s, a in accts.items() if a and needs_settle(a))
            if n: msg.append(f'settled {n}'); accts = fb('acct') or {}
            publish(accts, prev)
            admin_tick(accts)
            cleanup_names(accts)
            fb('pub/meta/robotAt', 'PUT', now_ms())
            print(datetime.datetime.now(IL).strftime('%d.%m %H:%M:%S'), ' · '.join(msg) or 'ok', flush=True)
        except Exception as ex:
            print('error:', repr(ex), flush=True)
        if once or time.time() - started > RUN_FOR: break
        time.sleep(POLL)
