"""Reproducible fictional chicken-chain data in schema-conforming CSV tables.

Generate first, then use build_workbook.py to assemble the XLSX with artifact_tool.
No records are based on an actual restaurant chain.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import csv, json, math, random

SEED=20261020
END=date(2026,10,18)
WEEKS=[END-timedelta(weeks=103-i) for i in range(104)]
REGIONS=[('WEST','West','America/Los_Angeles',
          ['Costa Mesa','Santa Ana','Long Beach','Pasadena','Oceanside','Irvine','Anaheim','Glendale','San Diego','Ventura']),
         ('SOUTHWEST','Southwest','America/Phoenix',
          ['Tempe','Mesa','Chandler','Scottsdale','Phoenix North','Phoenix Central','Gilbert','Peoria','Tucson','Flagstaff']),
         ('MIDWEST','Midwest','America/Chicago',
          ['Naperville','Evanston','Oak Park','Schaumburg','Aurora','Joliet','Elgin','Chicago Loop','Tinley Park','Skokie']),
         ('SOUTHEAST','Southeast','America/New_York',
          ['Atlanta','Decatur','Marietta','Roswell','Alpharetta','Sandy Springs','Duluth','Smyrna','Brookhaven','Dunwoody'])]
MENU_ITEMS=[
 ('M001','Original Crispy Sandwich','Sandwiches',9.29,.178,'2022-01-01'),
 ('M002','Spicy Crispy Sandwich','Sandwiches',9.49,.118,'2022-01-01'),
 ('M003','Grilled Chicken Sandwich','Sandwiches',9.99,.066,'2022-01-01'),
 ('M004','Three-Piece Tenders','Tenders',10.99,.111,'2022-01-01'),
 ('M005','Five-Piece Tenders','Tenders',13.49,.074,'2022-01-01'),
 ('M006','Buffalo Chicken Wrap','Wraps',10.19,.043,'2022-01-01'),
 ('M007','Ranch Chicken Wrap','Wraps',9.89,.036,'2022-01-01'),
 ('M008','Grilled Chicken Rice Bowl','Bowls',12.49,.069,'2022-01-01'),
 ('M009','Crispy Chicken Rice Bowl','Bowls',12.49,.064,'2022-01-01'),
 ('M010','Southwest Chicken Salad','Salads',11.49,.034,'2022-01-01'),
 ('M011','Seasoned Waffle Fries','Sides',3.79,.075,'2022-01-01'),
 ('M012','Creamy Slaw','Sides',3.29,.022,'2022-01-01'),
 ('M013','Mac & Cheese Cup','Sides',4.49,.031,'2022-01-01'),
 ('M014','Chicken Breakfast Biscuit','Breakfast',6.99,.037,'2022-01-01'),
 ('M015','Breakfast Chicken Wrap','Breakfast',7.49,.031,'2022-01-01'),
 ('M016','House Lemonade','Beverages',3.49,.047,'2022-01-01'),
 ('M017','Fountain Soda','Beverages',2.99,.050,'2022-01-01'),
 ('M018','Handspun Shake','Beverages',5.49,.031,'2022-01-01'),
 ('M019','Honey Heat Chicken Wrap','Wraps',10.49,.028,'2026-04-01'),
]
TABLES=['Restaurant_Master','Menu_Master','Source_Log','Store_Week_Status','Sales_Weekly','Menu_Weekly','Promotions_Weekly','Financials_Weekly']

def spread(total,weights):
    """Largest remainder: deterministic integer partition, exact sum."""
    assert total>=0 and weights and sum(weights)>0
    z=[total*w/sum(weights) for w in weights]
    i=[math.floor(v) for v in z]
    for ix in sorted(range(len(i)),key=lambda x:(-(z[x]-i[x]),x))[:total-sum(i)]:
        i[ix]+=1
    assert sum(i)==total
    return i

def cash(cents):
    return f'{cents/100:.2f}'

def d(d): return d.isoformat() if d else ''

def create(seed=SEED):
    rng=random.Random(seed)
    t={name:[] for name in TABLES}
    t['Menu_Master']=[dict(zip(('menu_item_id','menu_item_name','menu_category','introduced_on','retired_on'),
            (m[0],m[1],m[2],m[5],''))) for m in MENU_ITEMS]
    t['Source_Log']=[
      {'source_id':'SYNTH-POS-01','source_type':'Synthetic POS export','origin_description':
        f'Lunch Rush fictional demo generator; seed {seed}; not real merchant data',
       'sales_basis':'Consumer restaurant POS: menu sales net of discounts and refunds; excludes taxes, tips, and third-party fees',
       'coverage_notes':'104 Sunday-ending reporting weeks, selected active stores; one intentionally partial feed for QA',
       'extracted_on':'2026-10-20'},
      {'source_id':'SYNTH-MENU-01','source_type':'Synthetic POS item export','origin_description':
        f'Lunch Rush fictional demo generator; seed {seed}; exact allocations to POS sales',
       'sales_basis':'Consumer restaurant POS: item net revenue allocated to match restaurant-week POS',
       'coverage_notes':'Item totals reconcile to POS for Complete menu status; one intentionally incomplete menu feed',
       'extracted_on':'2026-10-20'},
      {'source_id':'SYNTH-STATUS-01','source_type':'Synthetic coverage log','origin_description':
        f'Lunch Rush fictional demo generator; seed {seed}; planned QA exceptions',
       'sales_basis':'Consumer restaurant POS coverage status only; no separate sales',
       'coverage_notes':'Realistic new openings, one disruption, one partial POS week, one partial menu week',
       'extracted_on':'2026-10-20'},
    ]
    restaurants=[]
    for region_i,(region,rname,tz,cities) in enumerate(REGIONS):
      for j,city in enumerate(cities):
        k=region_i*10+j+1
        fmt=['Drive-Thru','Dine-In','Pickup-Focused','Drive-Thru','Dine-In'][j%5]
        owner='Franchise' if k%3==0 or k%7==0 else 'Company'
        if j<=6:
            opened=date(2021+k%3,1+(k*3)%12,1+(k*5)%26)
        elif j<=8:
            opened=date(2025,2+(j-7)*4,6+(k%4)*4)
        else:
            opened=date(2026,3+region_i,12+(k%3)*4)
        item={'restaurant_id':f'R{k:03}','restaurant_name':city,
          'region_id':region,'region_name':rname,'ownership_type':owner,
          'restaurant_format':fmt,'opened_on':d(opened),'closed_on':'','timezone':tz}
        restaurants.append(item);t['Restaurant_Master'].append(item)

    # A fixed store-specific factor creates good and weak locations even within a region.
    base_factors={r['restaurant_id']:rng.uniform(.78,1.23) for r in restaurants}
    for wi,week in enumerate(WEEKS):
      week_start=week-timedelta(days=6)
      months=(week.year-2024)*12+week.month-10
      season=1+.055*math.sin((week.timetuple().tm_yday/365)*math.tau) + (.11 if week.month==12 else 0)
      for r in restaurants:
        rid=r['restaurant_id']; opened=date.fromisoformat(r['opened_on'])
        if opened>week: continue
        expected=min(7,(week-max(opened,week_start)).days+1)
        disrupt=(rid=='R018' and week==date(2026,8,9))
        active_days=3 if disrupt else expected
        partial_pos=rid=='R009' and week==date(2026,6,28)
        partial_menu=rid=='R014' and week==date(2026,6,14)
        t['Store_Week_Status'].append({'week_end':d(week),'restaurant_id':rid,
          'expected_operating_days':expected,'actual_operating_days':active_days,
          'coverage_status':'Partial' if partial_pos else 'Complete',
          'menu_coverage_status':'Partial' if (partial_menu or partial_pos) else 'Complete',
          'disruption_flag':'TRUE' if disrupt else 'FALSE','source_id':'SYNTH-STATUS-01'})
        region=r['region_id']; fmt=r['restaurant_format']
        base_daily={'Drive-Thru':580,'Dine-In':365,'Pickup-Focused':270}[fmt]
        if region=='WEST': base_daily*=1.06
        if region=='MIDWEST': base_daily*=.93
        if region=='SOUTHEAST': base_daily*=1.03
        traffic_trend=1+wi*.0002
        # Last 13 weeks: realistic chainwide trade-down in transaction volume, strongest in Midwest/West.
        after_2026_summer=week>=date(2026,7,26)
        current_drag={'WEST':.91,'SOUTHWEST':.98,'MIDWEST':.86,'SOUTHEAST':1.01}[region] if after_2026_summer else 1
        if rid in ('R004','R021','R028') and after_2026_summer: current_drag*=.96
        if rid in ('R012','R033') and after_2026_summer: current_drag*=1.10
        tx_total=max(1,round(base_daily*active_days*base_factors[rid]*season*traffic_trend*current_drag*rng.uniform(.96,1.04)))
        if fmt=='Drive-Thru':
            ch={'Drive-Thru':.59,'Dine-In':.16,'Pickup':.15,'Delivery':.10}
        elif fmt=='Dine-In':
            ch={'Dine-In':.58,'Pickup':.23,'Delivery':.19}
        else:
            ch={'Dine-In':.10,'Pickup':.57,'Delivery':.33}
        # Consumers have been shifting towards delivery over the two years.
        add_delivery=.047*wi/103
        if 'Drive-Thru' in ch: ch['Drive-Thru']-=add_delivery
        else: ch['Dine-In']-=add_delivery*.75;ch['Pickup']-=add_delivery*.25
        ch['Delivery']+=add_delivery
        dayparts={'Breakfast':.15,'Lunch':.47,'Dinner':.38}
        combos=[(channel,part) for channel in ch for part in dayparts]
        # Per-store-week channel/daypart transactions mutually exclusive.
        txn=spread(tx_total,[ch[channel]*share*rng.uniform(.96,1.04) for channel,part in combos for p,share in dayparts.items() if p==part])
        # Rates and inflation affect average check, independent of volume.
        prices_increase=1+0.058*wi/52
        pos=[];net_total=0
        for (channel,part),n in zip(combos,txn):
            uplift={'Delivery':1.12,'Pickup':1.02,'Drive-Thru':1.00,'Dine-In':.98}[channel]
            part_factor={'Breakfast':.69,'Lunch':1.00,'Dinner':1.13}[part]
            check=15.50*uplift*part_factor*prices_increase*rng.uniform(.985,1.015)
            gross=round(n*check*100)
            discount=round(gross*rng.uniform(.028,.047))
            refund=round(gross*rng.uniform(.002,.005))
            net=gross-discount-refund
            pos.append({'week_end':d(week),'restaurant_id':rid,'channel':channel,
                'daypart':part,'gross_sales_usd':cash(gross),'discount_usd':cash(discount),
                'refund_usd':cash(refund),'net_sales_usd':cash(net),
                'transaction_count':n,'source_id':'SYNTH-POS-01'})
            net_total+=net
        # Remove one known part of a partial feed, rather than pretending it is zero.
        if partial_pos:
            pos=[x for x in pos if not (x['channel']=='Delivery' and x['daypart']=='Dinner')]
            net_total=round(sum(Decimal(x['net_sales_usd'])*100 for x in pos))
        t['Sales_Weekly'].extend(pos)
        active=[m for m in MENU_ITEMS if date.fromisoformat(m[5])<=week]
        weights=[]
        for m in active:
            w=m[4]
            if m[0]=='M002' and after_2026_summer: w*=.55  # spicy sandwich decline
            if m[2]=='Bowls' and after_2026_summer: w*=1.13
            if m[2]=='Breakfast' and fmt=='Pickup-Focused': w*=.8
            weights.append(w*rng.uniform(.94,1.06))
        if partial_menu:
            active=[m for m in active if m[0] not in ('M002','M018')]
            weights=[m[4] for m in active]  # intentionally missing itemized sales; not a whole-store menu
        # For complete POS+menu weeks enforce exact equality, down to a single cent.
        # For partially covered item feeds intentionally leave a visible unreconciled gap.
        target=round(net_total*.86) if partial_menu else net_total
        item_cents=spread(target,weights)
        for m,rev in zip(active,item_cents):
            if rev<1:continue
            units=max(1,round(rev/100/m[3]))
            item_orders=min(units,tx_total)
            t['Menu_Weekly'].append({'week_end':d(week),'restaurant_id':rid,'menu_item_id':m[0],
                 'units_sold':units,'item_order_count':item_orders,
                 'item_net_sales_usd':cash(rev),'source_id':'SYNTH-MENU-01'})
    return t


def write_csv_tables(tabs,out,schema):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for name in TABLES:
        headers=[x['name'] for x in schema['tables'][name]['fields']]
        with (out/(name+'.csv')).open('w',newline='',encoding='utf-8') as fp:
            writer=csv.DictWriter(fp,fieldnames=headers);writer.writeheader();writer.writerows(tabs[name])
    manifest={'synthetic':True,'generator_seed':SEED,'start_week':d(WEEKS[0]),'end_week':d(WEEKS[-1]),
              'weeks':len(WEEKS),'rows':{n:len(tabs[n]) for n in TABLES},
              'source':'Entirely generated demo; not based on confidential or actual chain records',
              'planned_scenarios':['West and Midwest Q3/Q4 2026 transaction softness','R009 partial POS week ending 2026-06-28','R014 partial menu week ending 2026-06-14',
                'R018 site disruption','Late-period spicy sandwich decline','Delivery mix increases over time','New site openings']}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest

if __name__=='__main__':
    from lunch_rush.engine import validate
    repo=Path(__file__).parent
    schema=json.loads((repo/'schema.json').read_text())
    tabs=create()
    r=validate(tabs,schema)
    print('Validation errors',len(r.errors),r.errors[:5]); r.assert_valid()
    manifest=write_csv_tables(tabs,repo/'work',schema)
    print(json.dumps(manifest,indent=2))
