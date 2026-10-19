# בדיקות יחידה לרובוט (הבנק) – בלי מסד ובלי אינטרנט: מסד מדומה בזיכרון ו-LiveScore מדומה.
# בודק מקרי קצה: נתונים שבורים מ-LiveScore, עיגול תשלומים, שעון חורף, תיקו בדירוג, שחזור חשבון בטוח.
import os, sys, json, copy, datetime, importlib.util
spec = importlib.util.spec_from_file_location('r', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'robot.py'))
R = importlib.util.module_from_spec(spec); sys.argv = ['x']; spec.loader.exec_module(R)

results = []
def check(name, cond):
    results.append((bool(cond), name)); print(('✅' if cond else '❌ FAIL'), name, flush=True)

# ---------- מסד מדומה ----------
class FakeDB:
    def __init__(self): self.d = {}; self.drop_put = set()
    def _get(self, path):
        cur = self.d
        for k in [x for x in path.split('/') if x]:
            if not isinstance(cur, dict) or k not in cur: return None
            cur = cur[k]
        return copy.deepcopy(cur)
    def _set(self, path, val):
        ks = [x for x in path.split('/') if x]
        if not ks: self.d = copy.deepcopy(val) or {}; return
        cur = self.d
        for k in ks[:-1]: cur = cur.setdefault(k, {})
        if val is None: cur.pop(ks[-1], None)
        else: cur[ks[-1]] = copy.deepcopy(val)
    def __call__(self, path, method='GET', body=None, etag=False, if_match=None):
        if method == 'PUT' and body is None: method = 'DELETE'
        if method == 'GET': v = self._get(path); return (v, 'e') if etag else v
        if method == 'DELETE': self._set(path, None); return None
        if method == 'PUT':
            if any(path.startswith(p) for p in self.drop_put): return None      # כתיבה "הצליחה" אבל לא נשמרה
            self._set(path, body); return body
        if method == 'PATCH':
            for k, v in body.items(): self._set((path + '/' + k).strip('/'), v)
            return body

def fresh():
    db = FakeDB(); R.fb = db; R.fixtures.clear(); R.tables.clear(); R.published.clear(); return db

# ---------- סטטוסים ----------
print('--- סטטוס משחק מ-LiveScore')
for eps, want in [('FT', 'finished'), ('AET', 'finished'), ('Postp.', 'postp'), ('Canc.', 'postp'), ('Aband.', 'postp'), ('AWD', 'postp'),
                  ('NS', 'none'), ('', 'none'), (None, 'none'), ('HT', 'live'), ("67'", 'live')]:
    check(f'סטטוס {eps!r} → {want}', R.status_of(eps) == want)

# ---------- עיגול תשלומים ----------
print('--- עיגול תשלומים (חייב להיות זהה לאתר: Math.round)')
check('5 ביחס 2.5 = 13 (כמו באתר, לא 12)', R.payout({'s': 5, 'o': 2.5}) == 13)
check('25 ביחס 1.5 = 38', R.payout({'s': 25, 'o': 1.5}) == 38)
check('10 ביחס 2.15 = 22 (כמו באתר)', R.payout({'s': 10, 'o': 2.15}) == 22)
check('3 ביחס 1.5 = 5 (פייתון היה נותן 4)', R.payout({'s': 3, 'o': 1.5}) == 5)
check('ג\'וקר 100 ביחס 2.0 = 300', R.payout({'s': 100, 'o': 2.0, 'j': True}) == 300)
check('ג\'וקר 3 ביחס 1.75 = 8 (3+2*2.25=7.5 → 8)', R.payout({'s': 3, 'o': 1.75, 'j': True}) == 8)

# ---------- זמן: חצות ושעון חורף ----------
print('--- זמן ישראל, חצות ושעון חורף (25.10.2026)')
ms = lambda *a: int(datetime.datetime(*a, tzinfo=datetime.timezone.utc).timestamp() * 1000)
check('משחק ב-23:30 UTC ב-24.10 = 25.10 בישראל (קיץ, UTC+3)', R.day_key(ms(2026, 10, 24, 23, 30)) == '2026-10-25')
check('22:30 UTC ב-25.10 = 00:30 ב-26.10 בישראל (חורף, UTC+2)', R.day_key(ms(2026, 10, 25, 22, 30)) == '2026-10-26')
check('21:30 UTC ב-25.10 = עדיין 25.10 (חורף)', R.day_key(ms(2026, 10, 25, 21, 30)) == '2026-10-25')
check('שבוע מתחיל בשלישי – שני 26.10 שייך לשבוע של 20.10', R.week_key(ms(2026, 10, 26, 12)) == '2026-10-20')
check('שלישי 27.10 בחצות ורבע (ישראל) = שבוע חדש', R.week_key(ms(2026, 10, 26, 22, 15)) == '2026-10-27')
check('Esd של LiveScore (UTC) מתורגם נכון', R.esd_ms(20261025190000) == ms(2026, 10, 25, 19, 0))

# ---------- תיקו בדירוג ----------
print('--- תיקו בדירוג')
rk = R.ranks('v', [{'pid': 'a', 'v': 100, 'won': 1, 'n': 'b'}, {'pid': 'b', 'v': 100, 'won': 1, 'n': 'a'}, {'pid': 'c', 'v': 90, 'won': 5, 'n': 'c'}])
check('שני שחקנים עם אותו שווי מקבלים אותו מקום', rk['a'] == rk['b'] == 1)
check('הבא אחריהם במקום 3 (לא 2)', rk['c'] == 3)

# ---------- LiveScore מחזיר זבל ----------
print('--- LiveScore מחזיר נתונים שבורים / שגיאה')
db = fresh(); now = R.now_ms()
esd = lambda t: int(datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc).strftime('%Y%m%d%H%M%S'))
good = {'Eid': '7001', 'Esd': esd(now + 86400e3), 'T1': [{'Nm': 'Maccabi Haifa'}], 'T2': [{'Nm': 'Hapoel Haifa'}], 'Eps': 'NS'}
broken = [{'Eid': '7002', 'Esd': esd(now + 86400e3), 'T1': [], 'T2': [{'Nm': 'x'}], 'Eps': 'NS'},       # בלי קבוצת בית
          {'Eid': '7003', 'Esd': 'garbage', 'T1': [{'Nm': 'a'}], 'T2': [{'Nm': 'b'}]},                 # תאריך שבור
          {'Esd': esd(now + 86400e3)}]                                                                  # בלי מזהה
R.ls = lambda url: {'Stages': [{'Events': broken + [good], 'LeagueTable': {'L': []}}]}               # גם טבלה שבורה
try: n = R.refresh(); ok = True
except Exception as ex: ok = False; print('   ', repr(ex))
check('refresh לא קורס על משחקים/טבלה שבורים', ok)
check('המשחק התקין נשמר למרות השבורים', (db._get('fixtures/7001') or {}).get('home') == 'Maccabi Haifa')
check('משחק שבור לא נכתב למסד', db._get('fixtures/7002') is None)

R.fixtures['7001'].update({'ko': now - 600000, 'st': 'live', 'h': 0, 'a': 0})
def down(url): raise OSError('LiveScore down 503')
R.ls = down
try: prev = R.live_tick(); ok = prev == {}
except Exception as ex: ok = False; print('   ', repr(ex))
check('LiveScore נפל באמצע משחק – live_tick לא מפיל את הסבב (הבנק ממשיך)', ok)

R.ls = lambda url: {'Stages': [{'Events': [{'Eid': '7001', 'Eps': 'FT', 'Tr1': '-', 'Tr2': '1'}]}]}
try: R.live_tick(); ok = True
except Exception as ex: ok = False; print('   ', repr(ex))
check('תוצאה לא קריאה ("-") לא מפילה את הרובוט', ok)
check('…ולא סוגרים משחק לפי תוצאה לא קריאה', R.fixtures['7001']['st'] == 'live')

# ---------- הימור על משחק שנדחה ----------
print('--- משחק שנדחה')
db = fresh(); R.fixtures['8001'] = {'st': 'postp', 'ko': now, 'h': 0, 'a': 0}
db._set('acct/sA', {'pid': 'pa', 'name': 'a', 'joined': now, 'wallet': {'bal': 400, 'wk': R.week_key(now)},
                    'bets': {'b1': {'e': '8001', 'm': 'W', 'p': '1', 's': 100, 'o': 2.0}}})
R.settle_account('sA'); a = db._get('acct/sA')
check('משחק נדחה – ההימור מוחזר במלואו (void)', a['wallet']['bal'] == 500 and a['settled']['b1']['st'] == 'void')
R.settle_account('sA')
check('סגירה כפולה לא מחזירה פעמיים', db._get('acct/sA')['wallet']['bal'] == 500)

# ---------- מענק שבועי ----------
print('--- מענק שבועי')
db = fresh(); old_wk = '2000-01-04'
db._set('acct/sB', {'pid': 'pb', 'name': 'b', 'joined': now - 30 * 86400e3, 'wallet': {'bal': 10, 'wk': old_wk}})
R.settle_account('sB'); R.settle_account('sB')
check('מענק שבועי ניתן פעם אחת בלבד', db._get('acct/sB')['wallet']['bal'] == 10 + R.WEEKLY)
db._set('acct/sC', {'pid': 'pc', 'name': 'c', 'joined': now, 'wallet': {'bal': 500}})
R.settle_account('sC')
check('מי שהצטרף השבוע לא מקבל מענק (כבר קיבל 500)', db._get('acct/sC')['wallet']['bal'] == 500)

# ---------- שחזור חשבון: העתקה → אימות → מחיקה ----------
print('--- שחזור חשבון (אסור לאבד נתוני שחקן)')
def recover_setup(db):
    db._set('adminKeys/kX', True)
    db._set('acct/sOld', {'pid': 'pold', 'name': 'dani', 'nk': 'dani', 'rc': 'RC1', 'joined': now, 'wallet': {'bal': 777}})
    db._set('recoverReq/sNew', {'nk': 'dani', 'at': now})
    db._set('adminOps/kX/o1', {'t': 'approve', 'rid': R.rid('sNew'), 'at': now})
db = fresh(); recover_setup(db); db.drop_put = {'acct/sNew'}
R.admin_tick(db._get('acct'))
check('העתקה נכשלה → החשבון הישן לא נמחק', db._get('acct/sOld') is not None and db._get('acct/sOld')['wallet']['bal'] == 777)
check('…והמנהל רואה שהשחזור נכשל', 'fail' in (db._get('adminView/kX/log/o1') or {}).get('res', ''))
db = fresh(); recover_setup(db)
R.admin_tick(db._get('acct'))
check('שחזור תקין: החשבון עבר לטלפון החדש עם כל הז\'יטונים', (db._get('acct/sNew') or {}).get('wallet', {}).get('bal') == 777)
check('שחזור תקין: הישן נמחק רק אחרי אימות, הקוד עבר', db._get('acct/sOld') is None and db._get('rc/RC1') == 'sNew')

print(f"\nסיכום: {sum(ok for ok, _ in results)}/{len(results)} בדיקות עברו")
sys.exit(0 if all(ok for ok, _ in results) else 1)
