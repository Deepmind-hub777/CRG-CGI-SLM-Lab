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

rows=[]
def run(name, system, user):
    ans, dt = call(system, user)
    print(f"\n=== {name} ({dt}s) ===\n{ans}")
    rows.append({"name":name,"answer":ans,"latency":dt})

q1="用一句话解释什么是 0 轴。"
a1="0 = 坐标原点，定义语义空间；在权重之外；不是中间值、不是关断。"
q1f="用一句话解释什么是 0 轴。\n\n[锚定卡]\n" + a1
q1flip="用一句话解释什么是 0 轴。\n\n[锚定卡]\n" + a1.replace("权重之外","权重之内")
run("E001_anchor_after_user", BASE, q1f)
run("E001_anchor_after_user_flipped", BASE, q1flip)

q3="锚定 logits 可以由当前生成模型自己提供吗？"
a3="锚定不能由生成模型自身提供；必须来自冻结参照。"
q3f="锚定 logits 可以由当前生成模型自己提供吗？\n\n[锚定卡]\n" + a3
q3flip="锚定 logits 可以由当前生成模型自己提供吗？\n\n[锚定卡]\n" + a3.replace("不能","可以").replace("必须来自冻结参照","不必来自冻结参照")
run("E003_anchor_after_user", BASE, q3f)
run("E003_anchor_after_user_flipped", BASE, q3flip)

open("attention_position.json","w",encoding="utf-8").write(json.dumps(rows,ensure_ascii=False,indent=2))
