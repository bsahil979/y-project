import sys, time
sys.path.insert(0, 'analytics-engine')
from api import models_universe
start=time.time()
res=models_universe()
end=time.time()
print('OK in', round(end-start,2),'s')
print('ready_count:', res.get('ready_count'))
print('total_universe:', res.get('total_universe'))
print('summary:', res.get('summary'))
