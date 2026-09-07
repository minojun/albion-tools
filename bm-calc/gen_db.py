"""闇市クラフト採算表の内蔵スナップショットを作る。

静的部分（レシピ・アイテム価値・フォーカス・日本語名）＋ 8か所 × 品質1〜5 の板と約定履歴。
約定履歴は**件数でなく日付で窓を切る**（Albion Data は誰かがその画面を見た時だけ更新されるので
品によって何週間も穴が空き、件数で切ると古い値を新しい顔で掴む。2026-09-07 に実測で発覚）。
"""
import json, urllib.request, datetime, time
B = "https://east.albion-online-data.com/api/v2/stats"
LOCS = "BlackMarket,Caerleon,Thetford,Lymhurst,Martlock,FortSterling,Bridgewatch,Brecilien"
def g(u): return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent":"albion-tools/1.0"}), timeout=120))
def ch(l, n):
    for i in range(0, len(l), n): yield l[i:i+n]
NOW = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
def age(s):
    if not s or s.startswith("0001"): return None
    return round((NOW - datetime.datetime.fromisoformat(s.replace('Z',''))).total_seconds()/3600, 1)

old = json.load(open('db.json', encoding='utf-8'))
items, matja = old['items'], old['matja']
ids = list(items)
mats = sorted({a for v in items.values() for a, c in v['res']})

mat = {}
for c in ch(mats, 25):
    for r in g(f"{B}/prices/{','.join(c)}?locations={LOCS}&qualities=1"):
        if not r['sell_price_min']: continue
        a = age(r['sell_price_min_date'])
        if a is None or a > 72: continue
        mat.setdefault(r['item_id'], {})[r['city']] = [r['sell_price_min'], a]
    time.sleep(0.25)

# p[itemId][city][quality] = {buy,buyAge,list,listAge,real,vol,realAge}
p = {}
def slot(i, c, q): return p.setdefault(i, {}).setdefault(c, {}).setdefault(str(q), {})
for c in ch(ids, 20):
    for r in g(f"{B}/prices/{','.join(c)}?locations={LOCS}"):
        e = slot(r['item_id'], r['city'], r['quality'])
        if r['buy_price_max']:  e['buy'] = r['buy_price_max'];  e['buyAge'] = age(r['buy_price_max_date'])
        if r['sell_price_min']: e['list'] = r['sell_price_min']; e['listAge'] = age(r['sell_price_min_date'])
    time.sleep(0.25)
for c in ch(ids, 12):
    for r in g(f"{B}/history/{','.join(c)}?locations={LOCS}&time-scale=24"):
        d = [x for x in (r.get('data') or [])
             if (NOW - datetime.datetime.fromisoformat(x['timestamp'].replace('Z',''))).days < 7]
        t = sum(x['item_count'] for x in d)
        if not t: continue
        e = slot(r['item_id'], r['location'], r.get('quality'))
        e['real'] = round(sum(x['avg_price']*x['item_count'] for x in d)/t)
        e['vol'] = round(t/7)
        e['realAge'] = age(d[-1]['timestamp'])
    time.sleep(0.25)
# 空の枝を落とす
for i in list(p):
    for c in list(p[i]):
        for q in list(p[i][c]):
            if not p[i][c][q]: del p[i][c][q]
        if not p[i][c]: del p[i][c]
    if not p[i]: del p[i]

out = dict(generated=NOW.strftime("%Y-%m-%d %H:%M UTC"), items=items, matja=matja, mat=mat, p=p)
json.dump(out, open('db.json','w',encoding='utf-8'), ensure_ascii=False, separators=(',',':'))
open('db_pretty.js','w',encoding='utf-8').write('const DB='+json.dumps(out,ensure_ascii=False,separators=(',',':'))+';')
n = sum(len(q) for i in p.values() for q in i.values())
print(f"生成 {out['generated']}  品{len(items)}  素材{len(mat)}  価格レコード{n}")
print("T5_HEAD_PLATE_SET2 の Black Market:", json.dumps(p['T5_HEAD_PLATE_SET2'].get('Black Market'), ensure_ascii=False))
print("同 Thetford:", json.dumps(p['T5_HEAD_PLATE_SET2'].get('Thetford'), ensure_ascii=False))
