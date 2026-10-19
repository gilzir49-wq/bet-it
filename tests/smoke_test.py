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

now = int(time.time() * 1000); E = '998' + str(now)[-6:]; E2 = '997' + str(now)[-6:]
R.fb(f'fixtures/{E}', 'PUT', {'lg': 'isr1', 'home': 'Maccabi Haifa', 'away': 'Hapoel Haifa', 'ko': now + 6 * 3600000, 'day': R.day_key(now + 6 * 3600000),
                              'st': 'none', 'h': 0, 'a': 0, 'odds': {'1': 2.0, 'X': 3.0, '2': 4.0, 'cs': {'1-0': 7.0}}})
name = 'smoke' + ''.join(secrets.choice(string.ascii_lowercase) for _ in range(6))
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
        check(len(code) == 12, 'הוצג קוד כניסה אישי'); pg.click('#final .btn.sec')
        extra = [ctx.new_page() for _ in range(3)]                 # עוד 3 לשוניות פתוחות – השמירה חייבת לעבוד
        for x in extra: x.goto('http://127.0.0.1:8765/index.html')
        pg.bring_to_front()
        pg.evaluate(f"() => {{ dayF = S.fixtures['{E}'].day; render(); }}")
        pg.wait_for_selector(f"button.ob[onclick*=\"'{E}','W','1'\"]", timeout=15000)
        pg.click(f"button.ob[onclick*=\"'{E}','W','1'\"]")
        pg.fill('#stakeIn', '50'); pg.click('#betBtn')
        pg.wait_for_function('() => A && A.wallet.bal === 450 && Object.keys(A.bets||{}).length === 1', timeout=20000)
        check(True, 'ההימור נשמר (יתרה 450)')
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
        pg.evaluate("() => { go('table'); leagueMenu(); }"); pg.fill('#lgName', 'smoke league'); pg.click("button[onclick='createLeague()']")
        pg.wait_for_function('() => A && A.leagues && Object.values(A.leagues).some(l => l.own)', timeout=20000)
        check(True, 'פתיחת ליגת חברים מהאפליקציה'); pg.wait_for_selector('#sheet a[href^="https://wa.me/"]', timeout=10000)
        check(pg.locator('#sheet a[href^="https://wa.me/"]').count() == 1, 'מסך הזמנה עם כפתור וואטסאפ'); pg.evaluate('() => closeSheet()')
        ctx2 = b.new_context(viewport={'width': 390, 'height': 844}); pg2 = ctx2.new_page()
        pg2.goto('http://127.0.0.1:8765/index.html'); pg2.wait_for_selector('#nameIn', timeout=20000)
        pg2.once('dialog', lambda d: d.accept(code))
        pg2.click("a[onclick^=\"loginWithCode\"]")
        pg2.wait_for_function(f'() => (typeof A!=="undefined" && A) && A.name === "{name}"', timeout=20000)
        check(True, 'כניסה ממכשיר אחר עם הקוד – אותו חשבון'); ctx2.close()
        check(not errs, 'אין שגיאות JavaScript בדף' + (f': {errs[:2]}' if errs else ''))
        b.close()
except Exception as ex:
    check(False, f'הבדיקה נתקעה: {ex}')
finally:
    s, a = acct()
    upd = {f'fixtures/{E}': None, f'fixtures/{E2}': None}
    if s: upd.update({f'acct/{s}': None, f"names/{a['nk']}": None}); upd.update({f"rc/{a['rc']}": None} if a.get('rc') else {}); upd.update({f'lgdef/{l}': None for l in (a.get('leagues') or {})})
    R.fb('', 'PATCH', upd); srv.shutdown()
sys.exit(1 if fails else 0)
