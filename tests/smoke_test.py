# בדיקת עשן בדפדפן אמיתי (Chromium) מול סביבת הבדיקה:
# משתמש חדש נכנס → מהמר → מרענן → ההימור עדיין שם (בשרת ובמסך) → מבטל → הז'יטונים חוזרים.
# אם משהו מזה נכשל – העדכון לא עולה לאתר.
import os, sys, json, time, importlib.util, threading, http.server, functools, secrets, string, urllib.request, urllib.parse
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

now = int(time.time() * 1000); E = '998' + str(now)[-6:]; E2 = '997' + str(now)[-6:]; E3 = '996' + str(now)[-6:]; E4 = '995' + str(now)[-6:]; CLEAN = {}
for _e, _h in ((E3, 7), (E4, 8)):
    R.fb(f'fixtures/{_e}', 'PUT', {'lg': 'isr1', 'home': 'Hapoel Tel Aviv', 'away': 'Beitar Jerusalem', 'ko': now + _h * 3600000, 'day': R.day_key(now + _h * 3600000),
                                   'st': 'none', 'h': 0, 'a': 0, 'odds': {'1': 2.2, 'X': 3.1, '2': 3.3}})
R.fb(f'fixtures/{E}', 'PUT', {'lg': 'isr1', 'home': 'Maccabi Haifa', 'away': 'Hapoel Haifa', 'ko': now + 6 * 3600000, 'day': R.day_key(now + 6 * 3600000),
                              'st': 'none', 'h': 0, 'a': 0, 'odds': {'1': 2.0, 'X': 3.0, '2': 4.0, 'cs': {'1-0': 7.0}}})
name = 'smoke' + ''.join(secrets.choice(string.ascii_lowercase) for _ in range(6)); RNAME = 'rest' + ''.join(secrets.choice(string.ascii_lowercase) for _ in range(6))
def acct():
    for s, a in (R.fb('acct') or {}).items():
        if a and a.get('name') == name: return s, a
    return None, None

SCORE_JS = r"""async () => {
  const E2='__E2__', f={id:E2,...S.fixtures[E2]}, H=he(f.home), W=he(f.away), out={};
  const esc=x=>x.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const pos=(root,re)=>{ const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT); let n;
    while((n=w.nextNode())){ re.lastIndex=0; const m=re.exec(n.data); if(m){ const r=document.createRange(); r.setStart(n,m.index); r.setEnd(n,m.index+m[0].length);
      const b=r.getBoundingClientRect(); if(b.width) return b.left+b.width/2; } } return null; };
  const dig=d=>new RegExp('(?<![\\d:]|\\d\\.)'+d+'(?![\\d:]|\\.\\d)');   // ספרה בודדת – לא חלק משעה/תאריך/יחס
  const judge=(where,root,names=true)=>{ if(!root){ out[where]={ok:false,err:'לא נמצא במסך'}; return; }
    const x8=pos(root,dig(8)), x6=pos(root,dig(6)), xh=names?pos(root,new RegExp(esc(H))):null, xa=names?pos(root,new RegExp(esc(W))):null;
    let ok=x8!=null&&x6!=null&&x8>x6;                                   // מימין לשמאל: הבית (8) מימין
    if(names) ok=ok&&xh!=null&&xa!=null&&xh>xa&&Math.abs(x8-xh)<Math.abs(x6-xh);
    out[where]={ok,x8,x6,xh,xa}; };
  const find=(sel,txt)=>[...document.querySelectorAll(sel)].filter(e=>e.textContent.includes(txt)).sort((a,b)=>a.textContent.length-b.textContent.length)[0];
  showGoal(f); judge('באנר גול', document.getElementById('goalbar'));
  go('games'); dayF='live'; render(); judge('כרטיס משחק חי', find('.teams',H));
  A.bets=A.bets||{}; A.bets.bqascore01={e:E2,m:'CS',p:'8-6',s:5,o:9,at:Date.now()};
  go('mine'); judge('ההימורים שלי – שורת לייב', find('.bc .lvt','לייב'), false); judge('ההימורים שלי – הימור תוצאה מדויקת', find('.bc .r3','תוצאה'), false);
  S.fixtures[E2].st='finished'; A.settled=A.settled||{}; A.settled.bqascore01={st:'won',pay:45,at:Date.now()};
  mineTab='hist'; go('mine'); judge('ההימורים שלי – היסטוריה ("נגמר X–Y")', find('.hr span','נגמר'), false);
  mineTab='open'; S.fixtures[E2].st='live'; delete A.settled.bqascore01;
  judge('pickLabel – תוצאה מדויקת בטקסט', (()=>{ const d=document.createElement('div'); d.dir='rtl'; d.style.cssText='position:fixed;top:0;right:0;font-size:16px';
    d.textContent=pickLabel(f,{m:'CS',p:'8-6'}); document.body.appendChild(d); setTimeout(()=>d.remove(),0); return d; })());
  S.revealed[E2]={a:{n:'דני',m:'W',p:'1',s:5,st:'live-win'},b:{n:'רוני',m:'W',p:'2',s:5,st:'live-lose'},c:{n:'משה',m:'CS',p:'8-6',s:5,st:'live-win'}};
  go('games'); dayF='live'; render(); judge('החבר׳ה על המשחק – תוצאה מדויקת נדירה', find('.crowdbox span','הלך על'), false);
  S.tables.isr1={rows:[{t:'Maccabi Haifa',pld:1,w:1,d:0,l:0,gf:1,ga:0,pts:3,img:''},{t:'Hapoel Haifa',pld:1,w:0,d:0,l:1,gf:0,ga:1,pts:0,img:''}]};
  lgF='isr1'; go('leagues'); judge('טבלת ליגה לייב', find('tr',H), false);
  delete A.bets.bqascore01; delete S.revealed[E2]; go('games');
  return out; }"""
OTHER_NAME = 'smokeother' + ''.join(secrets.choice(string.ascii_lowercase) for _ in range(5))
OTHER_SEC, OTHER_PID = 's' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48)), 'p' + ''.join(secrets.choice(string.ascii_lowercase) for _ in range(16))
OTHER_RC = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(12))
R.fb('', 'PATCH', {f'names/{OTHER_NAME}': OTHER_PID, f'rc/{OTHER_RC}': OTHER_SEC, f'acct/{OTHER_SEC}': {'name': OTHER_NAME, 'nk': OTHER_NAME, 'pid': OTHER_PID, 'rc': OTHER_RC, 'joined': now, 'wallet': {'bal': 500, 'op': 'init'}}})
dlg = []
fails = []
def check(cond, msg):
    print(('✅ ' if cond else '❌ ') + msg, flush=True)
    if not cond: fails.append(msg)

try:
    with sync_playwright() as p:
        b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='he-IL'); pg = ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://127.0.0.1:8765/index.html'); pg.wait_for_selector('#nameIn', timeout=20000)
        pg.fill('#nameIn', name); pg.click('#loginBtn')
        pg.wait_for_function('() => (typeof A!=="undefined" && A) && A.wallet && A.wallet.bal === 500', timeout=20000)
        check(True, 'משתמש חדש נכנס וקיבל 500')
        pg.wait_for_selector('#final.show', timeout=10000); code = pg.locator('#final div[style*="letter-spacing"]').inner_text().replace('-', '').strip()
        check(len(code) == 12, 'הוצג קוד כניסה אישי')
        pg.evaluate("() => { window.__wa=null; window.open=u=>{ window.__wa=u; return null; }; }"); pg.click('#waSelf')
        wa = urllib.parse.unquote(pg.evaluate('() => window.__wa') or '')
        check(wa.startswith('https://wa.me/?text=') and 'הכניסה שלי ל-BET-IT' in wa and '/#code=' + code in wa and 'לא לשתף' in wa, 'שלח לעצמי בוואטסאפ – הודעה עם קוד ולינק אישי')
        check(pg.evaluate("() => { const f=document.getElementById('pmForm'); return !!f && f.querySelector('[autocomplete=username]').value===A.name && f.querySelector('[autocomplete=new-password]').value===A.rc; }"), 'טופס למנהל הסיסמאות (שם + קוד)')
        pg.click('#final .btn.sec')
        pg.evaluate("() => { setScope('all'); go('table'); }")
        check(pg.locator('#firstGuess').count() == 1 and 'עוד לא ניחשת' in pg.locator('.mys').first.inner_text(), 'ארצית: מי שעוד לא ניחש – "עוד לא ניחשת" + כפתור לניחוש הראשון')
        pg.evaluate("() => go('games')")
        extra = [ctx.new_page() for _ in range(3)]                 # עוד 3 לשוניות פתוחות – השמירה חייבת לעבוד
        for x in extra: x.goto('http://127.0.0.1:8765/index.html')
        pg.bring_to_front()
        pg.evaluate(f"() => {{ dayF = S.fixtures['{E}'].day; render(); }}")
        pg.wait_for_selector(f"button.ob[onclick*=\"'{E}','W','1'\"]", timeout=15000)
        pg.click(f"button.ob[onclick*=\"'{E}','W','1'\"]")
        pg.fill('#stakeIn', '50'); pg.click('#betBtn')
        pg.wait_for_function('() => A && A.wallet.bal === 450 && Object.keys(A.bets||{}).length === 1', timeout=20000)
        check(True, 'ההימור נשמר (יתרה 450)')
        pg.evaluate("() => { setScope('all'); go('table'); }")
        check(pg.locator('#firstGuess').count() == 0, 'ארצית: אחרי ניחוש ראשון – הקריאה לפעולה נעלמת')
        me0 = pg.evaluate('() => A.pid'); ST0 = R.fb('pub/standings')
        R.fb('pub/standings', 'PUT', {'day': R.official_day(now), 'at': now, 'bank': 10000, 'rows': [
            {'pid': me0, 'n': name, 'pf': 40, 'won': 3, 'dn': 4, 'nb': 5, 'rk': 1, 'pp': 2}, {'pid': 'pzzzzzzzzzzzz1', 'n': 'זר', 'pf': -10, 'won': 1, 'dn': 2, 'nb': 2, 'rk': 2, 'pp': 1}]})
        pg.wait_for_function('() => S.standings && S.standings.rows && S.standings.rows.some(r => r.pf === 40)', timeout=15000)
        pg.evaluate('() => { tblLive=false; render(); }'); txt = pg.locator('#app').inner_text()   # הבדיקה הזו – על הדירוג הרשמי
        check('3/4 פגעו' in txt and '+40' in txt and 'אתה' in pg.locator('.lbd .r.me').inner_text(), 'טבלה: רווח כולל (+40), "3/4 פגעו" ותג "אתה"')
        check('עודכן לאחרונה' in pg.locator('#tblInfo').inner_text() and 'שבועית' not in txt, 'טבלה: "עודכן לאחרונה", בלי טבלה שבועית')
        check(pg.locator('.lbd .r.me .rk i').first.inner_text().strip().startswith('▲'), 'חץ: עלית מקום מאתמול')
        R.fb('pub/standings', 'PUT', ST0); pg.evaluate("() => { tblLive=null; go('games'); }")
        sec, a = acct(); check(a and a['wallet']['bal'] == 450 and len(a.get('bets') or {}) == 1, 'ההימור קיים בשרת')
        pg.reload(); pg.wait_for_function('() => (typeof A!=="undefined" && A) && A.wallet && Object.keys(A.bets||{}).length === 1', timeout=20000)
        check(True, 'אחרי רענון – ההימור עדיין שם')
        pg.evaluate(f"() => {{ go('games'); dayF = S.fixtures['{E}'].day; render(); }}")
        check(pg.locator('.mybet').count() >= 1, 'ההימור מוצג בכרטיס המשחק')
        pg.once('dialog', lambda d: d.accept())
        pg.click("[onclick^=\"cancelBet\"]")
        pg.wait_for_function('() => A && A.wallet.bal === 500 && Object.keys(A.bets||{}).length === 0', timeout=20000)
        check(True, 'ביטול החזיר את הז\'יטונים (500)')
        sec, a = acct(); check(a and a['wallet']['bal'] == 500, 'הביטול נשמר בשרת')
        # תור הימורים: היחס השתנה בזמן שלא הייתה קליטה → לא שולחים ביחס אחר
        pg.evaluate(f"async () => {{ QUEUE=[{{bid:'bqaodds'+Date.now().toString(36), e:'{E}', m:'W', p:'1', s:10, o:1.55, j:false}}]; saveQ(); await flushQueue(); }}")
        check(pg.evaluate('() => QUEUE.length === 0 && Object.keys(A.bets||{}).length === 0 && A.wallet.bal === 500'), 'הימור מהתור לא נשלח כשהיחס השתנה')
        # לינק זדוני שמנסה להשתיל הימור בתור / מפתח מזויף דרך #mig=
        ctx3 = b.new_context(); pg3 = ctx3.new_page(); pg3.on('pageerror', lambda e: errs.append(str(e)))
        evil = urllib.parse.quote(urllib.parse.urlencode({'bb_q': json.dumps([{'bid': 'bevil0001', 'e': E, 'm': 'W', 'p': '2', 's': 500}]), 'bb_sec': 'not-a-key"<x>', 'bb_tab': 'x'}))
        pg3.goto('http://127.0.0.1:8765/index.html#mig=' + evil); pg3.wait_for_selector('#nameIn', timeout=20000)
        check(pg3.evaluate("() => !localStorage.getItem('bb_q') && !localStorage.getItem('bb_sec') && !localStorage.getItem('bb_tab')"), 'לינק זדוני (#mig) לא משתיל הימורים או מפתחות')
        ctx3.close()
        # כיוון התוצאה: באתר מימין-לשמאל שערי הבית חייבים להופיע בצד של קבוצת הבית (בדיקה לפי מיקום בפיקסלים)
        R.fb(f'fixtures/{E2}', 'PUT', {'lg': 'isr1', 'home': 'Maccabi Haifa', 'away': 'Hapoel Haifa', 'ko': now - 3600000, 'day': R.day_key(now),
                                       'st': 'live', 'min': "67'", 'h': 8, 'a': 6, 'odds': {'1': 2.0, 'X': 3.0, '2': 4.0}})
        pg.wait_for_function(f"() => S.fixtures['{E2}'] && S.fixtures['{E2}'].h === 8", timeout=15000)
        res = pg.evaluate(SCORE_JS.replace('__E2__', E2))
        for where, r in res.items():
            check(r.get('ok'), f'תוצאה בכיוון הנכון (שערי הבית ליד קבוצת הבית): {where}' + ('' if r.get('ok') else f' {r}'))
        # --- טבלה: דירוג לייב + לחיצה על שחקן מראה רק הימורים על משחקים שהתחילו
        me1 = pg.evaluate('() => A.pid'); LV0 = R.fb('pub/standingsLive')
        pg.evaluate(f"async () => {{ await write('PATCH','',{{['acct/'+SEC+'/bets/bopen77x01']:{{e:'{E}',m:'W',p:'2',s:77,o:4.0,at:SV}},['acct/'+SEC+'/wallet/bal']:A.wallet.bal-77,['acct/'+SEC+'/wallet/op']:'b:bopen77x01'}}); }}")
        R.fb('', 'PATCH', {f'pub/revealed/{E2}': {f'{me1}_bseen00001': {'n': name, 'm': 'W', 'p': '1', 's': 30, 'o': 2.0, 'j': False, 'st': 'live-win'}},
                           'pub/standingsLive': {'live': True, 'at': now, 'rows': [{'pid': me1, 'n': name, 'pf': 30, 'won': 1, 'dn': 2, 'rk': 1, 'pp': 2}]}})
        pg.wait_for_function("() => S.stLive && S.stLive.rows && S.stLive.rows.length === 1 && S.revealed && Object.keys(S.revealed).length", timeout=15000)
        pg.evaluate("() => { tblLive=null; setScope('all'); go('table'); }")
        check(pg.locator('#liveSw button.on').inner_text().strip() == '🔴 לייב' and 'לייב' in pg.locator('#tblInfo').inner_text(), 'יש משחק חי → הטבלה פותחת בדירוג לייב')
        pg.click(f'.lbd .r[data-pid="{me1}"]'); pg.wait_for_selector('#pbets', timeout=5000); pt = pg.locator('#sheet').inner_text()
        check('ביחס 2.00' in pt and 'כרגע זוכה' in pt and '+30' in pt and '50% מתוך 2' in pt.replace('\n', ' '), 'לחיצה על שחקן: ההימורים שלו על משחקים שהתחילו + רווח, פגיעות, % מתוך N')
        check('77' not in pt, 'לחיצה על שחקן: הימור על משחק שעוד לא התחיל – לא מוצג')
        pg.evaluate('() => closeSheet()'); pg.click('#liveSw button:nth-child(2)')
        check('עודכן לאחרונה' in pg.locator('#tblInfo').inner_text() or 'הלילה' in pg.locator('#tblInfo').inner_text(), 'מתג "רשמי (23:59)" מחזיר לדירוג היומי')
        pg.evaluate("async () => { const b=A.bets.bopen77x01; await write('PATCH','',{['acct/'+SEC+'/bets/bopen77x01']:null,['acct/'+SEC+'/wallet/bal']:A.wallet.bal+77,['acct/'+SEC+'/wallet/op']:'c:bopen77x01'}); tblLive=null; go('games'); }")
        R.fb('', 'PATCH', {f'pub/revealed/{E2}': None, 'pub/standingsLive': LV0})
        pg.evaluate("() => { go('table'); leagueMenu(); }"); pg.fill('#lgName', 'smoke league'); pg.click("button[onclick='createLeague()']")
        pg.wait_for_function('() => A && A.leagues && Object.values(A.leagues).some(l => l.own)', timeout=20000)
        check(True, 'פתיחת ליגת חברים מהאפליקציה'); pg.wait_for_selector('#sheet a[href^="https://wa.me/"]', timeout=10000)
        check(pg.locator('#sheet a[href^="https://wa.me/"]').count() == 1, 'מסך הזמנה עם כפתור וואטסאפ'); pg.evaluate('() => closeSheet()')
        # --- פרטיות ליגות: הטלפון מאזין רק לליגה שלו; ליגות אחרות – רק מספר
        lid = pg.evaluate('() => Object.keys(A.leagues).find(l => A.leagues[l].own)'); me = pg.evaluate('() => A.pid')
        R.fb('', 'PATCH', {f'pub/lg/{lid}': {'n': 'smoke league', 'o': me, 'm': {me: name}, 'at': now}, 'pub/lg/ZZZZZZ': {'n': 'ליגה של אחרים', 'o': 'px', 'm': {'px': 'זר'}}})   # שאריות ישנות
        pg.evaluate(f"() => {{ unsubs['lg_{lid}']&&unsubs['lg_{lid}'](); delete lgSubs['{lid}']; lgStreams(); }}"); pg.wait_for_timeout(2500)
        check(pg.evaluate(f"() => !S.lg['{lid}']"), 'האתר לא קורא יותר את pub/lg (רק lgv)')
        R.fb('', 'PATCH', {f'lgv/{lid}': {'n': 'smoke league', 'o': me, 'm': {me: name, 'pquietmember01': 'חבר שקט'}, 'at': now, 'rk': {'rk': 2, 'of': 5, 'avg': 640}}, 'pub/stats': {'leagues': 6, 'players': 40}})
        pg.wait_for_function(f"() => S.lg['{lid}'] && S.lg['{lid}'].rk && S.stats && S.stats.leagues === 6", timeout=15000)
        check(pg.evaluate("() => Object.keys(S.lg).length === 1 && !S.lg.ZZZZZZ"), 'פרטיות: בטלפון יש רק את הליגה שלי (לא של אחרים)')
        pg.evaluate("() => { tblLive=false; setScope('all'); go('table'); }")
        check('smoke league' in pg.locator('#lgCards').inner_text() and pg.locator('#lgCards .lgcard').count() == 1, 'מסך הטבלה: כרטיס ליגה גדול בראש ("👥 smoke league · מקום … ›")')
        pg.click('#lgCards .lgcard'); pg.wait_for_selector('.hub', timeout=5000); lt = pg.locator('#app').inner_text()
        check('חבר שקט' in lt and 'עוד לא ניחש' in lt, 'טבלת ליגה: כל החברים – גם מי שעוד לא ניחש (בתחתית, "עוד לא ניחש")')
        pg.evaluate("() => { S.standings={day:'x',at:Date.now(),rows:[]}; render(); }")
        check(pg.locator('#offEmpty').count() == 1 and '23:59' in pg.locator('#offEmpty').inner_text(), 'טבלה רשמית בלי ניחושים שנסגרו – הסבר ידידותי במקום אפסים')
        pg.evaluate("() => { tblLive=null; setScope('all'); }")
        pg.evaluate("() => { go('table'); setScope('all'); setNS('leagues'); }")
        t = pg.locator('#lgOthers').inner_text(); check('יש עוד 5 ליגות חברים' in t and 'ליגה של אחרים' not in pg.content(), 'ליגות אחרות: רק "יש עוד 5 ליגות" בלי שמות')
        check('מקום 2 מתוך 5' in pg.content(), 'הדירוג של הליגה שלי מול כל הליגות')
        R.fb('', 'PATCH', {'pub/lg/ZZZZZZ': None}); CLEAN.update({f'pub/lg/{lid}': None, f'lgv/{lid}': None})
        pg.evaluate("() => { setNS('players'); go('games'); }")
        pg.evaluate("() => go('mine')"); pg.click('#fbBtn'); pg.fill('#fbIn', 'בדיקת פידבק – "אחלה" משחק'); pg.click('#fbGo')
        pg.wait_for_function('() => A && A.fbk && Object.keys(A.fbk).length === 1', timeout=15000); check(True, 'שליחת פידבק')
        ctx2 = b.new_context(viewport={'width': 390, 'height': 844}); pg2 = ctx2.new_page()
        pg2.goto('http://127.0.0.1:8765/index.html'); pg2.wait_for_selector('#nameIn', timeout=20000)
        pg2.click("a[onclick^=\"loginWithCode\"]"); pg2.wait_for_selector('#codeIn', timeout=5000)
        check(pg2.get_attribute('#codeIn', 'autocomplete') == 'current-password' and pg2.get_attribute('#codeUser', 'autocomplete') == 'username', 'מסך כניסה עם קוד – שדה שמנהל הסיסמאות מציע')
        pg2.fill('#codeIn', code); pg2.click('#codeGo')
        pg2.wait_for_function(f'() => (typeof A!=="undefined" && A) && A.name === "{name}"', timeout=20000)
        check(True, 'כניסה ממכשיר אחר עם הקוד – אותו חשבון'); ctx2.close()
        # --- שחזור עצמי: לינק אישי #code=
        ctx4 = b.new_context(viewport={'width': 390, 'height': 844}); pg4 = ctx4.new_page(); pg4.on('pageerror', lambda e: errs.append(str(e)))
        pg4.goto(f'http://127.0.0.1:8765/index.html#code={code}')
        check(pg4.evaluate('() => !location.hash.includes("code") && !location.href.includes("' + code + '")'), 'הלינק האישי נמחק מהכתובת מיד בטעינה')
        pg4.wait_for_function(f'() => (typeof A!=="undefined" && A) && A.name === "{name}"', timeout=20000)
        check(pg4.evaluate("() => !!localStorage.getItem('bb_sec')"), 'כניסה דרך הלינק האישי בטלפון חדש – אותו חשבון')
        # מחובר לחשבון אחד ופותח לינק של חשבון אחר → שואל, ולא מחליף בשקט
        pg4.once('dialog', lambda d: (dlg.append(d.message), d.dismiss()))
        pg4.goto(f'http://127.0.0.1:8765/index.html#code={OTHER_RC}'); pg4.wait_for_timeout(4000)
        check(dlg and OTHER_NAME in dlg[-1] and pg4.evaluate(f'() => A && A.name === "{name}"'), 'לינק של חשבון אחר – שואל "להחליף?" וביטול משאיר את החשבון הנוכחי')
        pg4.once('dialog', lambda d: d.accept())
        pg4.goto(f'http://127.0.0.1:8765/index.html#code={OTHER_RC}')
        pg4.wait_for_function(f'() => A && A.name === "{OTHER_NAME}"', timeout=20000); check(True, 'אישור – עובר לחשבון השני')
        pg4.goto('http://127.0.0.1:8765/index.html#code=ZZZZ<img src=x onerror=alert(1)>'); pg4.wait_for_timeout(2500)
        check(pg4.evaluate(f'() => !location.hash && A && A.name === "{OTHER_NAME}"'), 'לינק שבור/זדוני – לא קורס, לא מחליף חשבון, הכתובת נוקתה')
        ctx4.close()
        # --- "משחקים לא נטענים": דפדפן שחוסם את ה-SDK של Firebase (בתוך וואטסאפ/אינסטגרם, חוסם פרסומות)
        ctxR = b.new_context(viewport={'width': 390, 'height': 844}); ctxR.route('**/www.gstatic.com/**', lambda r: r.abort())
        pgR = ctxR.new_page(); pgR.on('pageerror', lambda e: errs.append(str(e))); pgR.goto('http://127.0.0.1:8765/index.html')
        pgR.wait_for_function(f"() => REST_MODE && S.fixtures && S.fixtures['{E}']", timeout=25000)
        check(True, 'SDK חסום → המשחקים נטענים בכל זאת (REST)')
        pgR.wait_for_selector('#nameIn', timeout=10000); pgR.fill('#nameIn', RNAME); pgR.click('#loginBtn')
        pgR.wait_for_function('() => A && A.wallet && A.wallet.bal === 500', timeout=25000); check(pgR.locator('#restBanner').count() == 1, 'SDK חסום → אפשר להירשם, ומוצג "חיבור מוגבל · נסה שוב"')
        pgR.wait_for_selector('#final.show', timeout=10000); pgR.click('#final .btn.sec')            # מסך "זה המפתח שלך" אחרי הרשמה
        pgR.wait_for_function("() => !document.getElementById('final').classList.contains('show')", timeout=5000)
        pgR.evaluate(f"() => {{ closeSheet(); go('games'); dayF=S.fixtures['{E}'].day; render(); }}")
        pgR.click(f"button.ob[onclick*=\"'{E}','W','1'\"]"); pgR.fill('#stakeIn', '20'); pgR.click('#betBtn')
        pgR.wait_for_function('() => A && A.wallet.bal === 480', timeout=25000)
        ra = [a for s_, a in (R.fb('acct') or {}).items() if a and a.get('name') == RNAME]
        check(ra and ra[0]['wallet']['bal'] == 480 and len(ra[0].get('bets') or {}) == 1, 'SDK חסום → הימור נשמר בשרת (REST)')
        ctxR.close()
        ctxX = b.new_context(); ctxX.route('**/*', lambda r: r.abort() if ('gstatic.com' in r.request.url or '.json' in r.request.url) else r.continue_())
        ctxX.add_init_script("localStorage.setItem('bb_sec','s'+'a'.repeat(48))")          # משתמש שכבר מחובר (רוב המשתמשים)
        pgX = ctxX.new_page(); pgX.goto('http://127.0.0.1:8765/index.html')
        pgX.wait_for_selector('#fxSlow #retryBtn', timeout=25000); check(True, 'אין חיבור בכלל → אחרי 15 שניות הסבר + "נסה שוב" (לא "מתחבר…" לנצח)')
        ctxX.close()
        check(not errs, 'אין שגיאות JavaScript בדף' + (f': {errs[:2]}' if errs else ''))
        b.close()
except Exception as ex:
    check(False, f'הבדיקה נתקעה: {ex}')
finally:
    s, a = acct()
    upd = {f'fixtures/{E}': None, f'fixtures/{E2}': None, f'fixtures/{E3}': None, f'fixtures/{E4}': None, **CLEAN}
    if s: upd.update({f'acct/{s}': None, f"names/{a['nk']}": None}); upd.update({f"rc/{a['rc']}": None} if a.get('rc') else {}); upd.update({f'lgdef/{l}': None for l in (a.get('leagues') or {})})
    upd.update({f'acct/{OTHER_SEC}': None, f'names/{OTHER_NAME}': None, f'rc/{OTHER_RC}': None, f'pub/profiles/{OTHER_PID}': None})
    for s_, a_ in (R.fb('acct') or {}).items():
        if a_ and a_.get('name') == RNAME: upd.update({f'acct/{s_}': None, f"names/{a_['nk']}": None, **({f"rc/{a_['rc']}": None} if a_.get('rc') else {})})
    R.fb('', 'PATCH', upd); srv.shutdown()
sys.exit(1 if fails else 0)
