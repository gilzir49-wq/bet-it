# רובוט BUX BET – "הבנק" המוסמך היחיד.
# מביא משחקים (היום + 3 ימים) מ-4 ליגות, יחסים, תוצאות לייב וטבלאות; סוגר הימורים ומשלם זכיות;
# מחלק מענק שבועי; מפרסם טבלאות דירוג, קופת בנק והימורים שנחשפו; מבצע פעולות מנהל.
# כותב ל-Firebase עם מפתח שירות (נשמר בכספת של GitHub, לא בקוד).
import json, time, math, os, sys, copy, threading, datetime, hashlib, urllib.request, urllib.error
from zoneinfo import ZoneInfo
from google.oauth2 import service_account
from google.auth.transport.requests import Request

DB = os.environ.get('DB_URL', 'https://buxbet-il-default-rtdb.europe-west1.firebasedatabase.app')
IL = ZoneInfo('Asia/Jerusalem')
LS = 'https://prod-public-api.livescore.com/v1/api/app'
LEAGUES = {'isr1': ('israel', 'premier-league'), 'isr2': ('israel', 'liga-leumit'),
           'eng': ('england', 'premier-league'), 'ita': ('italy', 'serie-a'),
           'ucl': ('champions-league', 'league-stage')}   # ליגת האלופות
DAYS_AHEAD = 7   # משחקים לשבוע קדימה
REFRESH_EVERY = 600
POLL = 20
RUN_FOR = 5 * 3600 + 40 * 60
MARGIN = 1.07
START, WEEKLY, BANK_START = 500, 50, 10000
LOCK_MS = 120000
REVEAL_MS = 4 * 86400 * 1000   # 'מי הימר מה' נשמר לכולם רק 4 ימים אחורה

# ---------- הרשאות ----------
_info = json.loads(os.environ['FIREBASE_SA']) if os.environ.get('FIREBASE_SA') else json.load(open(os.path.expanduser('~/.config/buxbet/sa.json')))
_creds = service_account.Credentials.from_service_account_info(_info, scopes=[
    'https://www.googleapis.com/auth/firebase.database', 'https://www.googleapis.com/auth/userinfo.email'])
def tok():
    if not _creds.valid: _creds.refresh(Request())
    return _creds.token

def fb(path, method='GET', body=None, etag=False, if_match=None):
    if method == 'GET' and not etag and path in MIRRORS:          # נתיב גדול שיש לו מראה חיה – בלי להוריד שוב מהשרת
        snap = MIRRORS[path].snapshot()
        if snap is not None: return snap
    if method == 'PUT' and body is None: method = 'DELETE'      # כתיבת "ריק" = מחיקה
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

# ---------- מראה חיה (סקייל) ----------
# במקום להוריד את כל החשבונות כל 20 שניות (10,000 שחקנים = מאות מגה בכל סבב), הרובוט פותח ערוץ האזנה אחד
# (REST streaming) ומקבל פעם אחת את הכול ואחר כך רק שינויים. אם הערוץ נופל/שותק – חוזרים אוטומטית לקריאה רגילה.
MIRRORS = {}
class Mirror:
    STALE = 120                                                  # Firebase שולח keep-alive כל ~30 שניות
    def __init__(self, path):
        self.path, self.data, self.ready, self.last = path, None, False, 0.0
        self.lock = threading.Lock(); MIRRORS[path] = self
        threading.Thread(target=self._run, daemon=True).start()
    def snapshot(self):
        with self.lock:
            if not self.ready or time.time() - self.last > self.STALE: return None
            return copy.deepcopy(self.data) if self.data is not None else {}
    @staticmethod
    def _set(node, ks, val):                                     # כמו Firebase: ריק = מחיקה, וצמתים ריקים נעלמים
        if not ks: return val if val not in ({}, None) else None
        node = node if isinstance(node, dict) else {}
        child = Mirror._set(node.get(ks[0]), ks[1:], val)
        if child is None: node.pop(ks[0], None)
        else: node[ks[0]] = child
        return node or None
    def _apply(self, kind, msg):
        ks = [k for k in (msg.get('path') or '/').split('/') if k]; val = msg.get('data')
        with self.lock:
            if kind == 'put' and not ks: self.data = val if isinstance(val, dict) else None; self.ready = True; return
            if not self.ready: return
            if kind == 'put': self.data = self._set(self.data, ks, val)
            else:
                for k, v in (val or {}).items(): self.data = self._set(self.data, ks + [x for x in k.split('/') if x], v)
    def _run(self):
        while True:
            try:
                req = urllib.request.Request(f'{DB}/{self.path}.json', headers={'Authorization': 'Bearer ' + tok(), 'Accept': 'text/event-stream'})
                with urllib.request.urlopen(req, timeout=90) as r:
                    kind = None
                    for raw in r:
                        line = raw.decode('utf-8').rstrip('\r\n')
                        if line.startswith('event:'): kind = line[6:].strip()
                        elif line.startswith('data:'):
                            self.last = time.time()
                            if kind in ('put', 'patch'): self._apply(kind, json.loads(line[5:]))
                            elif kind in ('cancel', 'auth_revoked'): break       # הטוקן פג (כל שעה) – מתחברים מחדש
            except Exception as ex: print('mirror', self.path, repr(ex), flush=True)
            with self.lock: self.ready = False
            time.sleep(3)

def fb_keys(path):
    """רק המפתחות (shallow) – בלי להוריד את כל התוכן."""
    req = urllib.request.Request(f'{DB}/{path}.json?shallow=true', headers={'Authorization': 'Bearer ' + tok()})
    with urllib.request.urlopen(req, timeout=20) as r: return list((json.loads(r.read().decode() or 'null') or {}).keys())

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
    if eps in ('Postp.', 'Canc.', 'Abd.', 'Susp.', 'Aband.', 'Abd', 'Canc', 'Cancl.', 'Postp', 'AWD', 'WO', 'Awarded'): return 'postp'
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
    for i in range(13):
        for j in range(13):
            p = poisson(i, lh) * poisson(j, la)
            if i > j: p1 += p
            elif i == j: px += p
            else: p2 += p
            if i <= 9 and j <= 9: cs[f'{i}-{j}'] = p          # תוצאה מדויקת: עד 9 שערים לכל צד
    o = lambda p, lo=1.05, hi=15: round(min(hi, max(lo, 1 / (p * MARGIN))), 2)
    return {'1': o(p1), 'X': o(px), '2': o(p2), 'cs': {k: o(p, 3.0, 250) for k, p in cs.items()}, 'lam': {'h': round(lh, 3), 'a': round(la, 3)}}

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
        try: rows = table_rows(st)
        except Exception as ex: print('table error', lg, repr(ex), flush=True); rows = []
        if rows: tables[lg] = rows; upd[f'pub/tables/{lg}'] = {'rows': rows, 'at': now}
        for e in st.get('Events', []):
            try:
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
            except Exception as ex: print('event error', lg, e.get('Eid'), repr(ex), flush=True)   # משחק אחד שבור לא עוצר את הבנק
    if upd: fb('', 'PATCH', upd)
    return sum(1 for k in upd if k.startswith('fixtures/'))

def live_tick():
    now = now_ms()
    need = [e for e, f in fixtures.items() if not f.get('manual') and f.get('st') in ('none', 'live')
            and f['ko'] <= now + 60000 and f['ko'] > now - 5 * 3600 * 1000]
    if not need: return {}
    ev = {}
    try:
        for dd in sorted({datetime.datetime.fromtimestamp(fixtures[e]['ko'] / 1000, datetime.timezone.utc).strftime('%Y%m%d') for e in need}):
            for s in ls(f'{LS}/date/soccer/{dd}/0?MD=1').get('Stages', []):
                for e in s.get('Events', []): ev[str(e['Eid'])] = e
    except Exception as ex: print('livescore error', repr(ex), flush=True); return {}   # בלי LiveScore – ממשיכים לסגור הימורים ולבצע פעולות מנהל
    upd, prev = {}, {}
    for eid in need:
        e = ev.get(eid)
        if not e: continue
        try:
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
        except Exception as ex: print('live event error', eid, repr(ex), flush=True)   # תוצאה לא קריאה – לא סוגרים לפיה
    if upd: fb('', 'PATCH', upd)
    return prev

# ---------- הימורים: מצב, תשלום ----------
sign = lambda n: (n > 0) - (n < 0)
def wins(f, b):
    if b['m'] == 'CS': return f"{f['h']}-{f['a']}" == b['p']
    return {'1': 1, 'X': 0, '2': -1}[b['p']] == sign(f['h'] - f['a'])
jsround = lambda x: int(math.floor(x + 0.5))   # בדיוק כמו Math.round באתר – השחקן מקבל את מה שהוצג לו
def payout(b): return jsround(b['s'] + 2 * (b['s'] * b['o'] - b['s'])) if b.get('j') else jsround(b['s'] * b['o'])
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
            if f and (f['st'] != 'none' or now >= f['ko'] - LOCK_MS) and f['ko'] > now - REVEAL_MS:   # נחשף רק אחרי הנעילה; ישנים לא נשלחים לכולם
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
    # כמה הימורים יש על כל משחק שעוד לא ננעל ("9 מהחבר׳ה כבר הימרו") – רק מספר, בלי לחשוף מה
    cnt = {}
    for a in accts.values():
        for b in ((a or {}).get('bets') or {}).values():
            f = fixtures.get(b['e'])
            if f and f['st'] == 'none' and now < f['ko'] - LOCK_MS: cnt[b['e']] = cnt.get(b['e'], 0) + 1
    if published.get('cnt') != json.dumps(cnt, sort_keys=True): upd_cnt = cnt
    else: upd_cnt = 'same'
    upd = {}
    if published.get('standings') != json.dumps(st_body, sort_keys=True): upd['pub/standings'] = {**st_body, 'at': now}
    if published.get('profiles') != json.dumps(profiles, sort_keys=True): upd['pub/profiles'] = profiles
    for e, v in revealed.items():
        if published.get('rv' + e) != json.dumps(v, sort_keys=True): upd[f'pub/revealed/{e}'] = v
    for k in [k for k in published if k.startswith('rv') and k[2:] not in revealed]:
        upd[f'pub/revealed/{k[2:]}'] = None; published.pop(k)       # משחק ישן – יוצא מהרשימה שכל טלפון מוריד (ההימורים עצמם נשארים בחשבונות)
    if upd_cnt != 'same': upd['pub/cnt'] = upd_cnt or None; published['cnt'] = json.dumps(cnt, sort_keys=True)
    if upd:
        fb('', 'PATCH', upd)
        published['standings'] = json.dumps(st_body, sort_keys=True); published['profiles'] = json.dumps(profiles, sort_keys=True)
        for e, v in revealed.items(): published['rv' + e] = json.dumps(v, sort_keys=True)

# ---------- ליגות חברים ----------
MAX_LEAGUES_PER_USER, MAX_MEMBERS = 10, 200
lg_first_seen = {}
def leagues_tick(accts):
    """בונה את ליגות החברים מהחשבונות (הרובוט הוא היחיד שמפרסם חברות), מבצע הרחקות, מנקה ליגות יתומות."""
    defs = fb('lgdef') or {}; bans = fb('lgban') or {}; out = {}
    for sec, a in accts.items():
        if not a or 'pid' not in a: continue
        mine = sorted((a.get('leagues') or {}).items(), key=lambda x: (x[1] or {}).get('at', 0))[:MAX_LEAGUES_PER_USER]
        for lid, e in mine:
            if lid not in defs or a['pid'] in (bans.get(lid) or {}): continue
            L = out.setdefault(lid, {'n': defs[lid].get('n', ''), 'm': {}, 'o': None, 'at': defs[lid].get('at', 0)})
            if (e or {}).get('own'): L['o'] = a['pid']
            if len(L['m']) < MAX_MEMBERS: L['m'][a['pid']] = a['name']
    # הרחקות – רק בעל הליגה
    by_pid = {a.get('pid'): s for s, a in accts.items() if a}
    for sec, a in accts.items():
        for lid, pids in ((a or {}).get('lgkick') or {}).items():
            L = out.get(lid)
            for pid in (pids or {}):
                if L and L['o'] == a.get('pid') and pid != a.get('pid'):
                    fb(f'lgban/{lid}/{pid}', 'PUT', True); L['m'].pop(pid, None)
                    if pid in by_pid: fb(f'acct/{by_pid[pid]}/leagues/{lid}', 'DELETE')
            fb(f'acct/{sec}/lgkick/{lid}', 'DELETE')
    # ליגה בלי בעלים (ספאם/נטושה) – נמחקת אחרי 10 דקות
    t = time.time(); dead = {}
    for lid in defs:
        if lid in out and out[lid]['o']: lg_first_seen.pop(lid, None); continue
        if t - lg_first_seen.setdefault(lid, t) > 600:
            dead[f'lgdef/{lid}'] = None; out.pop(lid, None); lg_first_seen.pop(lid, None)
    for i in range(0, len(dead), 500):
        fb('', 'PATCH', dict(list(dead.items())[i:i + 500]))
    out = {k: v for k, v in out.items() if v['o']}
    sig = json.dumps(out, sort_keys=True)
    if not published.get('lg_gone'): fb('pub/lg', 'DELETE'); published['lg_gone'] = True     # פרטיות: הרשימה הציבורית של כל הליגות נמחקה (פעם בהפעלה)
    # פרטיות: כל ליגה בנתיב משלה lgv/<קוד> (קריא רק למי שיודע את הקוד), ולכולם רק מספרים
    V = {r['pid']: r['v'] for r in json.loads(published.get('standings') or '{}').get('rows', [])}
    rk = sorted(((lid, len(L['m']), sum(V.get(p, 0) for p in L['m']) / max(1, len(L['m']))) for lid, L in out.items() if len(L['m']) >= 2), key=lambda x: (-x[2], -x[1], x[0]))
    rkof = {lid: {'rk': i + 1, 'of': len(rk), 'avg': round(avg)} for i, (lid, c, avg) in enumerate(rk)}
    upd = {}
    for lid, L in out.items():
        body = {'n': L['n'], 'o': L['o'], 'm': L['m'], 'at': L['at'], 'rk': rkof.get(lid)}
        if published.get('lgv' + lid) != json.dumps(body, sort_keys=True):
            upd.update({f'lgv/{lid}/{k}': v for k, v in body.items()}); published['lgv' + lid] = json.dumps(body, sort_keys=True)
    for k in [k for k in published if k.startswith('lgv') and k[3:] not in out]:
        upd[f'lgv/{k[3:]}'] = None; published.pop(k)                      # ליגה שנמחקה
    stats = {'leagues': len(out), 'players': len(by_pid)}
    if published.get('stats') != json.dumps(stats, sort_keys=True): upd['pub/stats'] = stats; published['stats'] = json.dumps(stats, sort_keys=True)
    if upd: fb('', 'PATCH', upd)
    return out

# ---------- ניקוי "המחזור השבועי" שבוטל (גל, 20.10.2026) ----------
# ערימות המחזור הן ערימה נפרדת (לא הכסף של השחקן). קודם מעתיקים לארכיון פרטי (archive/ – לא קריא מבחוץ),
# מוודאים שההעתקה נשמרה, ורק אז מוחקים – ורק את הנתיבים של המחזור. היתרה הראשית (wallet) והימורים רגילים לא נוגעים.
ROUND_KEYS = ('rd', 'rdpick', 'mt', 'mtown')
LGV_ROUND_KEYS = ('rd', 'rdst', 'rdsum')
def cleanup_rounds(accts):
    n = 0
    for sec, a in accts.items():
        old = {k: a[k] for k in ROUND_KEYS if isinstance(a, dict) and a.get(k) is not None}
        if not old: continue
        fb(f'archive/rounds/acct/{sec}', 'PATCH', old)
        got = fb(f'archive/rounds/acct/{sec}') or {}
        if any(got.get(k) != v for k, v in old.items()): continue                         # לא נשמר – לא מוחקים
        fb('', 'PATCH', {f'acct/{sec}/{k}': None for k in old}); n += 1
    if not published.get('lgv_rounds_clean'):
        for lid in fb_keys('lgv'):
            L = fb(f'lgv/{lid}') or {}; old = {k: L[k] for k in LGV_ROUND_KEYS if L.get(k) is not None}
            if not old: continue
            fb(f'archive/rounds/lgv/{lid}', 'PATCH', old)
            if any((fb(f'archive/rounds/lgv/{lid}/{k}')) != v for k, v in old.items()): continue
            fb('', 'PATCH', {f'lgv/{lid}/{k}': None for k in old}); n += 1
        published['lgv_rounds_clean'] = True
    return n

# ---------- פידבק משחקנים → מסך המנהל ----------
FB_KEEP, FB_PER_ACCT = 200, 20
fb_log = {}            # fid -> {...} (נטען מ-adminFb בהפעלה)
def feedback_tick(accts):
    keys = None; dele = {}; new = 0
    for sec, a in accts.items():
        items = sorted(((a or {}).get('fbk') or {}).items(), key=lambda x: -((x[1] or {}).get('at', 0)))
        for i, (fid, x) in enumerate(items):
            dele[f'acct/{sec}/fbk/{fid}'] = None
            if i < FB_PER_ACCT and isinstance(x, dict) and fid not in fb_log and isinstance(x.get('t'), str):   # הצפה מחשבון אחד – רק 20 אחרונים
                fb_log[fid] = {'t': x['t'][:500], 'at': x.get('at', 0), 'pid': a.get('pid'), 'n': a.get('name', '')}; new += 1
    if not dele: return 0
    for fid in sorted(fb_log, key=lambda k: fb_log[k]['at'])[:-FB_KEEP]: fb_log.pop(fid)   # רק 200 אחרונים
    fb('adminFb', 'PUT', fb_log or None)                     # קודם שומרים (לא קריא מבחוץ) …
    keys = fb('adminKeys') or {}
    for k in keys: fb(f'adminView/{k}/fb', 'PUT', fb_log or None)
    for i in range(0, len(dele), 500): fb('', 'PATCH', dict(list(dele.items())[i:i + 500]))   # … ורק אז מוחקים מהחשבון
    return new

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
                        else:
                            cur = fb(f'acct/{old[0]}') or old[1]                          # העותק הכי עדכני (לא מהסריקה)
                            fb(f'acct/{s2}', 'PUT', cur)
                            if fb(f'acct/{s2}') != cur: res = 'copy failed – nothing deleted'   # העתקה → אימות → רק אז מחיקה
                            else:
                                if cur.get('rc'): fb(f"rc/{cur['rc']}", 'PUT', s2)       # קוד הכניסה עובר לטלפון החדש
                                fb(f'acct/{old[0]}', 'DELETE'); fb(f'recoverReq/{s2}', 'DELETE')
                    else: fb(f'recoverReq/{s2}', 'DELETE')
                elif t == 'delete':
                    hit = next(((s, a) for s, a in accts.items() if a and a.get('pid') == op.get('pid')), None)
                    if hit: fb('', 'PATCH', {f'acct/{hit[0]}': None, f"names/{hit[1]['nk']}": None, f"pub/profiles/{hit[1]['pid']}": None,
                                              **({f"rc/{hit[1]['rc']}": None} if hit[1].get('rc') else {})})
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

_last_backup = [0]
def trigger_backup():
    """הגיבוי של GitHub לפי שעון מתעכב לפעמים בשעות – הרובוט (שרץ כל הזמן) מפעיל אותו בעצמו כל שעה."""
    tok_gh = os.environ.get('GITHUB_TOKEN')
    if not tok_gh or time.time() - _last_backup[0] < 3600: return
    _last_backup[0] = time.time()
    try:
        req = urllib.request.Request('https://api.github.com/repos/gilzir49-wq/bet-it/actions/workflows/backup.yml/dispatches', method='POST',
                                     data=json.dumps({'ref': 'master'}).encode(),
                                     headers={'Authorization': 'Bearer ' + tok_gh, 'Accept': 'application/vnd.github+json'})
        urllib.request.urlopen(req, timeout=20); print('backup triggered', flush=True)
    except Exception as ex: print('backup trigger failed:', ex, flush=True)

def heal_codes(accts):
    """קוד כניסה תמיד מצביע לחשבון הנכון (תיקון עצמי אם משהו השתבש, למשל אחרי שחזור)."""
    rcmap = fb('rc') or {}
    for sec, a in accts.items():
        rc = (a or {}).get('rc')
        if rc and rcmap.get(rc) != sec:
            fb(f'rc/{rc}', 'PUT', sec); print('healed code link for', a.get('name'), flush=True)

def cleanup_names(accts):
    """שמות שנתפסו בלי חשבון (ספאם) – נמחקים אחרי 3 דקות."""
    names = fb('names') or {}; pids = {a.get('pid') for a in accts.values() if a}; t = time.time()
    dead = {}
    for nk, pid in names.items():
        if pid in pids: orphan_seen.pop(nk, None); continue
        if t - orphan_seen.setdefault(nk, t) > 180: dead[f'names/{nk}'] = None; orphan_seen.pop(nk, None)
    for i in range(0, len(dead), 500):          # מחיקה בקבוצות – גם הצפה של אלפי שמות לא תוקעת את הרובוט
        fb('', 'PATCH', dict(list(dead.items())[i:i + 500]))

# ---------- לולאה ----------
if __name__ == '__main__':
    once = '--once' in sys.argv; started = time.time()
    fixtures.update(fb('fixtures') or {})
    for lg, v in (fb('pub/tables') or {}).items(): tables[lg] = v.get('rows', [])
    for e in (fb('pub/revealed') or {}): published['rv' + e] = ''        # כך ישנים יימחקו בסבב הראשון
    fb_log.update(fb('adminFb') or {})
    for lid in fb_keys('lgv'): published['lgv' + lid] = ''           # כך ליגות שנמחקו יימחקו גם מ-lgv
    if not once:
        for p in ('acct', 'names', 'lgdef'): Mirror(p)
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
            leagues_tick(accts)
            n_clean = cleanup_rounds(accts)
            if n_clean: msg.append(f'rounds cleaned {n_clean}')
            if feedback_tick(accts): msg.append('feedback')
            cleanup_names(accts)
            trigger_backup()
            if int(time.time()) % 300 < POLL: heal_codes(accts)   # כל ~5 דקות
            fb('pub/meta/robotAt', 'PUT', now_ms())
            print(datetime.datetime.now(IL).strftime('%d.%m %H:%M:%S'), ' · '.join(msg) or 'ok', flush=True)
        except Exception as ex:
            print('error:', repr(ex), flush=True)
        if once or time.time() - started > RUN_FOR: break
        time.sleep(POLL)
