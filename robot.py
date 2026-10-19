# רובוט BUX BET: מביא משחקים ל-3 ימים קדימה מ-4 ליגות, יחסי זכייה, תוצאות לייב וטבלאות ליגה.
# רץ בענן של GitHub (Actions) כל הזמן. כותב ל-Firebase, והאפליקציה מתעדכנת אצל כולם מיד.
import json, time, math, urllib.request, datetime, sys
from zoneinfo import ZoneInfo

DB = 'https://command-center-gal-default-rtdb.europe-west1.firebasedatabase.app'
NODE = next((a for a in sys.argv[1:] if not a.startswith('--')), 'bux-bet')
IL = ZoneInfo('Asia/Jerusalem')
LS = 'https://prod-public-api.livescore.com/v1/api/app'
LEAGUES = {   # קוד באפליקציה ← (מדינה, ליגה) ב-LiveScore
    'isr1': ('israel', 'premier-league'),
    'isr2': ('israel', 'liga-leumit'),
    'eng':  ('england', 'premier-league'),
    'ita':  ('italy', 'serie-a'),
}
DAYS_AHEAD = 3
REFRESH_EVERY = 600        # משחקים + טבלאות + יחסים: כל 10 דקות
POLL = 20                  # תוצאות לייב: כל 20 שניות
RUN_FOR = 5 * 3600 + 40 * 60   # GitHub מגביל ריצה ל-6 שעות; ריצה חדשה מתחילה אוטומטית
MARGIN = 1.07              # עמלת הבנק ביחסים

def http(url, method='GET', body=None):
    req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode() or 'null')

def esd_to_ms(esd):   # 20261019173000 (UTC) → epoch ms
    s = str(esd)
    dt = datetime.datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]), int(s[8:10]), int(s[10:12]), tzinfo=datetime.timezone.utc)
    return int(dt.timestamp() * 1000)

def status_of(eps):
    eps = (eps or '').strip()
    if eps in ('FT', 'AET', 'AP', 'Ended'): return 'finished'
    if eps in ('Postp.', 'Canc.', 'Abd.', 'Susp.'): return 'postp'
    if eps in ('NS', '', 'TBA', 'Delayed'): return 'none'
    return 'live'

# ---------- יחסי זכייה: מודל פואסון לפי כוח התקפה/הגנה מהטבלה ----------
def poisson(k, lam): return math.exp(-lam) * lam ** k / math.factorial(k)

def calc_odds(table, home, away):
    rows = {r['t']: r for r in table}
    tp = sum(r['pld'] for r in table) or 1
    mu = max(0.6, sum(r['gf'] for r in table) / tp)            # ממוצע שערים לקבוצה למשחק
    def strength(t, key):
        r = rows.get(t)
        if not r or not r['pld']: return 1.0
        raw = (r[key] / r['pld']) / mu
        w = r['pld'] / (r['pld'] + 5)                            # מתחילת עונה – מתונים
        return 1 + (raw - 1) * w
    lh = max(0.25, mu * strength(home, 'gf') * strength(away, 'ga') * 1.12)
    la = max(0.2, mu * strength(away, 'gf') * strength(home, 'ga') * 0.9)
    p1 = px = p2 = 0.0; cs = {}
    for i in range(9):
        for j in range(9):
            p = poisson(i, lh) * poisson(j, la)
            if i > j: p1 += p
            elif i == j: px += p
            else: p2 += p
            if i <= 4 and j <= 4: cs[f'{i}-{j}'] = p
    o = lambda p, lo=1.05, hi=15: round(min(hi, max(lo, 1 / (p * MARGIN))), 2)
    return {'1': o(p1), 'X': o(px), '2': o(p2), 'cs': {k: o(p, 3.0, 80) for k, p in cs.items()}}

# ---------- מצב ----------
fixtures = {}     # eid → fixture (עותק מקומי של מה שב-Firebase)
tables = {}       # lg → rows

def table_rows(st):
    lt = st.get('LeagueTable')
    if not lt: return []
    t = lt['L'][0]['Tables'][0]['team']
    return [{'t': r['Tnm'], 'img': r.get('Img') or '', 'pld': r['pld'], 'w': r['win'], 'd': r['drw'], 'l': r['lst'],
             'gf': r['gf'], 'ga': r['ga'], 'pts': r['pts']} for r in t]

def pld_of(lg, team):
    for r in tables.get(lg, []):
        if r['t'] == team: return r['pld']
    return None

def refresh():
    """משחקים בחלון (היום + 3 ימים), טבלאות ויחסים."""
    now = time.time() * 1000
    today = datetime.datetime.now(IL).replace(hour=0, minute=0, second=0, microsecond=0)
    win_from = today.timestamp() * 1000
    win_to = (today + datetime.timedelta(days=DAYS_AHEAD + 1)).timestamp() * 1000
    upd = {}
    for lg, (c, s) in LEAGUES.items():
        try:
            d = http(f'{LS}/stage/soccer/{c}/{s}/0?MD=1')
        except Exception as ex:
            print('stage error', lg, ex, flush=True); continue
        st = d['Stages'][0]
        rows = table_rows(st)
        if rows:
            tables[lg] = rows
            upd[f'tables/{lg}'] = {'rows': rows, 'at': int(now)}
        for e in st.get('Events', []):
            eid = str(e['Eid']); ko = esd_to_ms(e['Esd'])
            f = fixtures.get(eid)
            if not f and not (win_from <= ko < win_to): continue
            nf = dict(f or {})
            nf.update({'lg': lg, 'home': e['T1'][0]['Nm'], 'away': e['T2'][0]['Nm'],
                       'hi': e['T1'][0].get('Img') or '', 'ai': e['T2'][0].get('Img') or '', 'ko': ko})
            stt = status_of(e.get('Eps'))
            if not f:
                nf.update({'st': stt, 'h': int(e.get('Tr1') or 0), 'a': int(e.get('Tr2') or 0)})
                if stt == 'finished': nf['inT'] = True      # משחק ישן – כבר בטבלה
            elif stt == 'postp':
                nf['st'] = 'postp'
            elif nf.get('st') == 'postp' and stt == 'none':
                nf['st'] = 'none'          # נקבע מחדש
            # יחסים מתעדכנים עד הנעילה (2 דק' לפני)
            if nf.get('st') == 'none' and ko - now > 120000 and rows:
                nf['odds'] = calc_odds(rows, nf['home'], nf['away'])
            # משחק שהסתיים – האם הטבלה כבר כוללת אותו?
            if nf.get('st') == 'finished' and not nf.get('inT') and nf.get('bh') is not None:
                p = pld_of(lg, nf['home'])
                if p is not None and p > nf['bh']: nf['inT'] = True
            if nf != f:
                fixtures[eid] = nf
                upd[f'fixtures/{eid}'] = nf
    if upd:
        http(f'{DB}/{NODE}.json', 'PATCH', upd)
    return len([1 for k in upd if k.startswith('fixtures/')])

def live_tick():
    """תוצאות לייב + דקה למשחקים שמתחילים / רצים עכשיו."""
    now = time.time() * 1000
    need = [eid for eid, f in fixtures.items()
            if f.get('st') in ('none', 'live') and f['ko'] <= now + 60000 and f['ko'] > now - 5 * 3600 * 1000]
    if not need: return 'idle'
    days = sorted({datetime.datetime.fromtimestamp(fixtures[e]['ko'] / 1000, datetime.timezone.utc).strftime('%Y%m%d') for e in need})
    ev = {}
    for dd in days:
        d = http(f'{LS}/date/soccer/{dd}/0?MD=1')
        for s in d.get('Stages', []):
            for e in s.get('Events', []): ev[str(e['Eid'])] = e
    upd, prev = {}, {}
    for eid in need:
        e = ev.get(eid)
        if not e: continue
        f = fixtures[eid]
        st = status_of(e.get('Eps'))
        h = int(e.get('Tr1') or 0) if st in ('live', 'finished') else 0
        a = int(e.get('Tr2') or 0) if st in ('live', 'finished') else 0
        mn = (e.get('Eps') or '').strip() if st == 'live' else ''
        nf = dict(f)
        if st == 'live' and f.get('bh') is None:
            nf['bh'] = pld_of(f['lg'], f['home']); nf['ba'] = pld_of(f['lg'], f['away'])   # מצב הטבלה לפני המשחק
        if (h, a, st) != (f.get('h'), f.get('a'), f.get('st')):
            prev[eid] = {'h': f.get('h', 0), 'a': f.get('a', 0), 'st': f.get('st')}
        nf.update({'st': st, 'h': h, 'a': a, 'min': mn})
        if st == 'finished':
            nf.pop('min', None)
            if nf.get('odds'): nf['odds'] = {k: v for k, v in nf['odds'].items() if k != 'cs'}   # מקטינים נתונים
        if nf != f:
            fixtures[eid] = nf
            upd[f'fixtures/{eid}'] = nf
    if prev:
        upd['meta/prev'] = {'r': prev, 't': int(now)}   # לחצים בטבלה ולבאנר "עלו בטבלה"
    if upd:
        http(f'{DB}/{NODE}.json', 'PATCH', upd)
    return f'live {len(need)}' + (f' · changed {list(prev)}' if prev else '')

if __name__ == '__main__':
    once = '--once' in sys.argv
    started = time.time()
    fixtures.update(http(f'{DB}/{NODE}/fixtures.json') or {})
    for lg, v in (http(f'{DB}/{NODE}/tables.json') or {}).items(): tables[lg] = v.get('rows', [])
    last_refresh = 0
    while True:
        try:
            msg = []
            if time.time() - last_refresh > REFRESH_EVERY:
                msg.append(f'refresh {refresh()}'); last_refresh = time.time()
            msg.append(live_tick())
            http(f'{DB}/{NODE}/meta/robotAt.json', 'PUT', int(time.time() * 1000))
            print(datetime.datetime.now(IL).strftime('%d.%m %H:%M:%S'), ' · '.join(msg), flush=True)
        except Exception as ex:
            print('error:', ex, flush=True)
        if once or time.time() - started > RUN_FOR: break
        time.sleep(POLL)
