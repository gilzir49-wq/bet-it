# בדיקת "המראה החיה" של הרובוט: אחרי כל סוג כתיבה (מלאה, חלקית, מרובת נתיבים, מחיקה) –
# העותק שבזיכרון של הרובוט חייב להיות זהה בדיוק למה שבשרת. כותב רק לנתיב בדיקה זמני, ומוחק אותו בסוף.
import os, sys, time, random, secrets, string, importlib.util
spec = importlib.util.spec_from_file_location('r', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'robot.py'))
R = importlib.util.module_from_spec(spec); sys.argv = ['x']; spec.loader.exec_module(R)

P = 'qa_mirror_' + ''.join(secrets.choice(string.ascii_lowercase) for _ in range(8))
results = []
def check(name, cond):
    results.append((bool(cond), name)); print(('✅' if cond else '❌ FAIL'), name, flush=True)
server = lambda: R.fb(P, etag=True)[0] or {}                      # etag=True – תמיד מהשרת, לא מהמראה
def same(timeout=8):
    t = time.time()
    while time.time() - t < timeout:
        if M.snapshot() == server(): return True
        time.sleep(0.3)
    print('   mirror:', M.snapshot(), '\n   server:', server()); return False

try:
    R.fb(P, 'PUT', {'s1': {'name': 'a', 'wallet': {'bal': 500, 'op': 'init'}}})
    M = R.Mirror(P)
    t = time.time()
    while M.snapshot() is None and time.time() - t < 15: time.sleep(0.3)
    check('המראה התחברה וקיבלה את כל הנתונים', M.snapshot() is not None and same())
    R.fb(f'{P}/s2', 'PUT', {'name': 'b', 'wallet': {'bal': 10}}); check('חשבון חדש (PUT)', same())
    R.fb('', 'PATCH', {f'{P}/s1/bets/b1': {'e': '1', 's': 50}, f'{P}/s1/wallet/bal': 450, f'{P}/s1/wallet/op': 'b:b1'}); check('הימור – כתיבה מרובת נתיבים מהשורש', same())
    R.fb(f'{P}/s1/wallet', 'PATCH', {'bal': 999, 'wk': 'w1'}); check('עדכון חלקי (PATCH)', same())
    R.fb('', 'PATCH', {f'{P}/s1/bets/b1': None, f'{P}/s1/wallet/bal': 500}); check('ביטול – מחיקה בתוך עדכון', same())
    R.fb(f'{P}/s2', 'DELETE'); check('מחיקת חשבון', same())
    R.fb(f'{P}/s1/settled', 'PUT', {'b9': {'st': 'won', 'pay': 10}}); R.fb(f'{P}/s1/settled/b9', 'DELETE'); check('צומת שהתרוקן נעלם (כמו בשרת)', same())
    rnd = random.Random(7)
    for i in range(40):                                                # כתיבות אקראיות
        sec = f's{rnd.randint(1, 5)}'; k = rnd.choice(['wallet/bal', 'bets/b' + str(rnd.randint(1, 4)), 'name', 'leagues/L' + str(rnd.randint(1, 3))])
        v = rnd.choice([None, rnd.randint(0, 99), {'at': i, 'x': rnd.randint(0, 9)}])
        m = rnd.choice(['PUT', 'PATCHROOT', 'PATCH'])
        if m == 'PUT': R.fb(f'{P}/{sec}/{k}', 'PUT', v)
        elif m == 'PATCHROOT': R.fb('', 'PATCH', {f'{P}/{sec}/{k}': v, f'{P}/{sec}/seen': i})
        else: R.fb(f'{P}/{sec}', 'PATCH', {k: v})
    check('40 כתיבות אקראיות – המראה זהה לשרת', same(15))
    R.fb(P, 'DELETE'); check('הכול נמחק – המראה ריקה', same() and M.snapshot() == {})
    M.last = 0; check('מראה ששתקה יותר מדי – הרובוט חוזר לקריאה רגילה מהשרת', M.snapshot() is None)
finally:
    R.fb(P, 'DELETE')
print(f"\nסיכום: {sum(ok for ok, _ in results)}/{len(results)} בדיקות עברו")
sys.exit(0 if all(ok for ok, _ in results) else 1)
