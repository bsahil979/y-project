import requests,json,time
from pathlib import Path
out=Path('research/live_smoke_2026-11-16');out.mkdir(exist_ok=True)
results=[]
def check(name,method,path,payload=None,expected=200):
 t=time.monotonic()
 try:
  r=requests.request(method,'http://127.0.0.1:8000'+path,json=payload,timeout=240)
  d=r.json();(out/(name+'.json')).write_text(json.dumps(d,indent=2),encoding='utf-8')
  row={'check':name,'status':r.status_code,'passed':r.status_code==expected,'seconds':round(time.monotonic()-t,2),'keys':list(d)[:16] if isinstance(d,dict) else []}
 except Exception as e:row={'check':name,'passed':False,'error':str(e)}
 results.append(row);print(json.dumps(row),flush=True);(out/'results.json').write_text(json.dumps(results,indent=2))
for name,path in [('models','/models/status'),('research','/research/evaluation-summary'),('advisor','/advisor/status'),('ppo','/ppo/status'),('tools','/tools')]:check(name,'GET',path)
check('invalid_horizon','GET','/forecast/MSFT?horizon=0',expected=400)
base={'tickers':['RELIANCE.NS','TCS.NS','INFY.NS','HDFCBANK.NS','ICICIBANK.NS'],'weights':[.2]*5,'start':'2023-01-01','end':'2026-01-01','benchmark':'^NSEI','include_optional_ml':False,'risk_preference':'conservative','investment_horizon_years':1}
check('portfolio','POST','/portfolio/analyze',base)
check('mixed_fx','POST','/portfolio/analyze',{'tickers':['MSFT','RELIANCE.NS'],'position_values':[1000,100000],'base_currency':'INR','start':'2023-01-01','end':'2026-01-01','include_optional_ml':False,'benchmark':'^NSEI','risk_preference':'conservative'})
check('optimization','POST','/portfolio/optimize',{'tickers':base['tickers'],'start_date':'2023-01-01','end_date':'2026-01-01','risk_preference':'aggressive','investment_horizon_years':1})
check('forecast','GET','/forecast/MSFT?horizon=5')
check('marketmind','GET','/marketmind/MSFT')
check('sentiment','GET','/sentiment/MSFT')
check('chat','POST','/chat',{'query':'Explain the difference between portfolio volatility and drawdown. Do not recommend a trade.','tickers':[]})
