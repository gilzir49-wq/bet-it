import json,time,secrets,string,urllib.request,urllib.error,sys,os,importlib.util,subprocess
DB=os.environ['DB_URL']
spec=importlib.util.spec_from_file_location('r',os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','robot.py')); R=importlib.util.module_from_spec(spec); sys.argv=['x']; spec.loader.exec_module(R)
def req(m,p,b=None):
    r=urllib.request.Request(f'{DB}/{p}.json',method=m,data=None if b is None else json.dumps(b).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(r,timeout=20) as x: return x.status,json.loads(x.read().decode() or 'null')
    except urllib.error.HTTPError as e: return e.code,None
rs=lambda n,a:''.join(secrets.choice(a) for _ in range(n)); AZM=string.ascii_letters+string.digits; AZ=string.ascii_lowercase+string.digits; SV={'.sv':'timestamp'}
now=int(time.time()*1000); E='999000003'; day=R.day_key(now+86400000)
R.fb(f'fixtures/{E}','PUT',{'lg':'isr1','home':'Maccabi Haifa','away':'Hapoel Haifa','ko':now+86400000,'day':day,'st':'none','h':0,'a':0,'odds':{'1':2.0,'X':3.0,'2':4.0,'cs':{'2-1':8.0}}})
sec,pid,nk='s'+rs(48,AZM),'p'+rs(16,AZ),'e2e_tester'
print('create', req('PATCH','',{f'names/{nk}':pid,f'acct/{sec}':{'name':'e2e_tester','nk':nk,'pid':pid,'joined':SV,'wallet':{'bal':500,'op':'init'}}})[0])
b=lambda bid,m,p,s,o,bal,j=False: {**{f'acct/{sec}/bets/{bid}':{'e':E,'m':m,'p':p,'s':s,'o':o,'at':SV,**({'j':True} if j else {})},f'acct/{sec}/wallet/bal':bal-s,f'acct/{sec}/wallet/op':'b:'+bid},**({f'acct/{sec}/jokers/{day}':bid} if j else {})}
print('bet W joker 100@2.0', req('PATCH','',b('be2e0000001','W','1',100,2.0,500,True))[0])
print('bet CS 50@8.0', req('PATCH','',b('be2e0000002','CS','2-1',50,8.0,400))[0])
print('bet X 50@3.0', req('PATCH','',b('be2e0000003','W','X',50,3.0,350))[0])
# המשחק נגמר 2-1 (רק המנהל/הרובוט יכולים לכתוב תוצאה)
R.fb(f'fixtures/{E}','PATCH',{'st':'finished','h':2,'a':1,'ko':now-3600000})
out=subprocess.run([sys.executable,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','robot.py'),'--once'],capture_output=True,text=True,env=os.environ); print('robot:', out.stdout.strip().splitlines()[-1:])
st,a=req('GET',f'acct/{sec}'); w=a['wallet']
# צפוי: 300 + ג'וקר 100+2*(200-100)=300 + מדויק 50*8=400 + תיקו 0 = 1000
assert w['bal']==1000, w; print('balance after settle:', w['bal'], '(expected 1000)', '| settled:', {k:v['st']+' '+str(v['pay']) for k,v in a.get('settled',{}).items()})
st,rv=req('GET',f'pub/revealed/{E}'); print('revealed after lock:', len(rv or {}), 'bets')
st,sd=req('GET','pub/standings'); row=[r for r in sd['rows'] if r['pid']==pid]; print('standings row:', row, '| bank:', sd['bank'])
# שחזור: טלפון חדש מבקש, מנהל מאשר
s2='s'+rs(48,AZM); print('recover req', req('PUT',f'recoverReq/{s2}',{'nk':nk,'at':SV})[0])
K='k'+rs(40,AZM); R.fb(f'adminKeys/{K}','PUT',True)
subprocess.run([sys.executable,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','robot.py'),'--once'],capture_output=True,text=True,env=os.environ)
st,av=req('GET',f'adminView/{K}'); r=[x for x in av.get('reqs',[]) if x['nk']==nk]; print('admin sees request:', bool(r))
print('admin approve', req('PUT',f'adminOps/{K}/oe2e1',{'t':'approve','rid':r[0]['rid'],'at':SV})[0])
subprocess.run([sys.executable,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','robot.py'),'--once'],capture_output=True,text=True,env=os.environ)
ok=req('GET',f'acct/{s2}')[1] is not None and req('GET',f'acct/{sec}')[1] is None; assert ok, 'recovery failed'; print('new phone has account:', req('GET',f'acct/{s2}')[1] is not None and req('GET',f'acct/{s2}')[1]['wallet']['bal']==1000, '| old key dead:', req('GET',f'acct/{sec}')[1] is None)
R.fb('','PATCH',{f'acct/{s2}':None,f'acct/{sec}':None,f'names/{nk}':None,f'fixtures/{E}':None,f'pub/revealed/{E}':None,f'pub/profiles/{pid}':None,f'adminView/{K}/log':None})
R.fb(f'adminKeys/{K}','DELETE'); print('cleaned')
