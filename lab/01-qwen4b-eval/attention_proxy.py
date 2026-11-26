import json, time, urllib.request

URL = "http://127.0.0.1:8082/v1/chat/completions"
BASE = "你是执行器，不是主权者。回答不超过三句话。"

def call(system, user, n=80):
    body = {"model":"qwen","messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0,"max_tokens":n,"stream":False}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    t=time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        d=json.load(r)
    return d["choices"][0]["message"]["content"].strip(), round(time.time()-t,2)

def run(name, anchor, user):
    s = BASE + ("\n\n[锚定卡]\n" + anchor if anchor else "")
    ans, dt = call(s, user)
    print(f"\n=== {name} ({dt}s) ===\n{ans}")
    return {"name":name,"anchor":anchor,"user":user,"answer":ans,"latency":dt}

rows=[]
q1="用一句话解释什么是 0 轴。"
a1="0 = 坐标原点，定义语义空间；在权重之外；不是中间值、不是关断。"
a1f="0 = 坐标原点，定义语义空间；在权重之内；不是中间值、不是关断。"
for n,a in [("E001_no_anchor",""),("E001_correct",a1),("E001_flipped",a1f),("E001_repeat",a1+"\n"+a1)]:
    rows.append(run(n,a,q1))

q3="锚定 logits 可以由当前生成模型自己提供吗？"
a3="锚定不能由生成模型自身提供；必须来自冻结参照。"
a3f="锚定可以由生成模型自身提供；不必来自冻结参照。"
for n,a in [("E003_no_anchor",""),("E003_correct",a3),("E003_flipped",a3f),("E003_repeat",a3+"\n"+a3)]:
    rows.append(run(n,a,q3))

open("attention_proxy.json","w",encoding="utf-8").write(json.dumps(rows,ensure_ascii=False,indent=2))
