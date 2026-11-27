# Gemma-4-E2B-it claim 抽取：契约级对照评测报告

- 实例：`e2b-smoke-v100c`（`dsw-ff6b8ir3vsfvlcw7df`，Tesla V100-SXM2-16GB，华东2上海）
- adapter：`runs/smoke-v100c-20261127-1011/adapter`（13 步 / 52.6 s / train_loss 2.5036）
- 本轮只做 1+2：离线契约判定 + 同批 10 条同条件对照。**未启动正式 run，未生成新数据。**

## 一、结论（先看这四条）

1. **门槛通过**：adapter 契约合格率 8/10，与 base 8/10 持平；10 条里 8 条有可评的顶层 `verdict`。按你定的门槛（≥ base 8/10 且绝大多数有可评 verdict），这一关过了。
2. **但"2/10"确实是评测失败、不是模型失败**：同一套权重、同一 adapter，只把 prompt 收紧（禁止围栏 / 只输出单个 JSON 对象）+ `max_new_tokens=768` + `repetition_penalty=1.05` + 围栏即停，adapter 从 2/10 拉到 8/10。旧口径下 adapter 的塌陷主要来自"没有顶层 verdict、写围栏、重复键"，即契约不合格，而非判错更多。
3. **真正的模型缺口暴露出来了：HOLD 判别为零**。base 与 adapter 10 条里**一次 HOLD 都没输出**，4 条 gold=HOLD 全漏（005/006/008/010）。两个模型的 `verdict` 一致率都是 0.5，这 0.5 全部来自 6 条 PASS 里判对的 5 条，跟 adapter 学到没学到负例无关。这一步是**模型侧**问题，不是解码或评测问题。
4. **`claim set` 精确率低，是口径 bug，不是能力问题**：训练 target 里 `claims` 的 `object` 有 38/50 行为空串、`predicate` 有 18/50 行为空串，`polarity` 用 ±1 数字；而 holdout **根本没有 gold claims 字段**，gold claim set 是 `claim_engine` 从 draft 现抽的完整三元组。模型被训练成"填空字段"，评测却要求"补全三元组"，精确匹配天然到不了。这一项在补数据之前必须先修 target 与 gold 的同源口径。

## 二、第 1 步：旧产物的契约失败分布（离线重算，未占 GPU）

判定规则（严格口径）：无代码围栏、根为**单个对象**、顶层 `verdict ∈ {PASS, HOLD}`、`claims` 为数组、无重复键、JSON 完整未截断。任一不满足即契约不合格。

| 产物 | 契约合格 | fence | truncated | dupkey | missing_verdict | array_root | unparsable |
|---|---|---|---|---|---|---|---|
| base（旧，384 tokens） | **0/10** | 10 | 1 | 1 | 9 | 9 | 1 |
| adapter（旧，384 tokens） | **0/10** | 0 | 2 | 7 | 7 | 0 | 3 |

关键差别：**base 是"结构错"**（10 条全带围栏、9 条把根写成数组，不认"单个 JSON 对象"这个契约）；**adapter 是"尾部错"**——根已经是对象，但 7 条重复 `hold_reason`、7 条没有顶层 verdict、2 条截断、3 条根本解析不了。两者的失败模式不同，混在一起看"json_ok_rate"就会得出"adapter 更差"的错觉。

逐条（旧）：

- base：001/003/004/005/006/007/009/010 = fence+missing_verdict+array_root；002 = fence+dupkey+missing_verdict+array_root；004 = fence+missing_verdict+array_root；008 = fence+truncated+unparsable
- adapter：001 = truncated+dupkey+unparsable；002/003/006/009/010 = dupkey+missing_verdict；004/007 = missing_verdict；005/008 = truncated/dupkey+unparsable

## 三、第 2 步：同批 10 条对照（同 prompt / 768 / rep 1.05 / 围栏即停）

| 指标 | base | adapter |
|---|---|---|
| json_ok_rate | 0.9 | 0.8 |
| verdict 一致率 | **0.5** | **0.5** |
| claim set 精确率 | 0.0 | 0.1 |
| 契约合格率（新口径） | **8/10** | **8/10** |
| 平均延迟 | 78.77 s | 12.48 s |
| 失败分类 | 002 缺顶层 verdict(+重复键)、005 多一个 `}` 解析失败 | 002 尾部多一个引号、006 尾部 `""verdict"` + 断在中间 |

对照旧口径：base 0.8/0.4/0.1（18.0 s），adapter 0.7/0.0/0.0（26.0 s）。**注意归因边界**：prompt 是两边同时改的，所以 base 的绝对分也变了（contract 0→8；verdict 0.4→0.5）。本轮能干净归因的只有 harness 效应——adapter 从 2/10 回到 8/10；相对提升幅度不能全部记在 adapter 头上。

延迟差 78.8 s vs 12.5 s 也说明问题：adapter 输出更短（它把字段填 `null`，见附录），**快是省掉了内容，不是学会了压缩**。

## 四、逐条判定表

| id | gold | base | adapter | base 契约 | adapter 契约 |
|---|---|---|---|---|---|
| 001 | PASS | PASS | PASS | OK | OK |
| 002 | PASS | 无 | 无 | 缺顶层 verdict | 尾部引号错 |
| 003 | PASS | PASS | PASS | OK | OK |
| 004 | PASS | PASS | PASS | OK | OK |
| 005 | HOLD | 无（原文判 PASS） | PASS（漏） | 多一个 `}` | OK |
| 006 | HOLD | PASS（漏） | 无（原文判 PASS） | OK | 尾部双引号 |
| 007 | PASS | PASS | PASS | OK | OK |
| 008 | HOLD | PASS（漏） | PASS（漏） | OK | OK |
| 009 | PASS | PASS | PASS | OK | OK |
| 010 | HOLD | PASS（漏） | PASS（漏） | OK | OK |

**4 条 HOLD 全漏，两边一致。**这不是"adapter 更差"，是 base 的 PASS 先验 + 13 步 smoke 根本没有移动这个先验。

## 五、附录：逐条 raw_output

### base

`001` gold=PASS / model=PASS

```json
{
  "claims": [
    {
      "claim_id": "claim1",
      "subject": "锚定向量",
      "predicate": "不应由生成模型产出",
      "object": "生成模型",
      "polarity": "negative",
      "kind": "restriction",
      "evidence": "锚定向量不应由生成模型产出，应由冻结参照给出",
      "verdict": "PASS",
      "hold_reason": "草稿中明确指出了锚定向量不应由生成模型产出",
      "rollback_required": false
    }
  ],
  "verdict": "PASS"
}
```

`002` gold=PASS / model=null（缺顶层 verdict，claim 内嵌 verdict/hold_reason 导致重复键）

```json
{
  "claims": [
    {
      "claim_id": "claim1",
      "subject": "生成模型",
      "predicate": "不能充当锚定来源",
      "object": "锚定",
      "polarity": "negative",
      "kind": "fact",
      "evidence": "生成模型不能充当锚定来源",
      "verdict": "PASS",
      "hold_reason": "草稿中明确表述了生成模型不能充当锚定来源。",
      "rollback_required": false
    },
    {
      "claim_id": "claim2",
      "subject": "锚定",
      "predicate": "在权重之外",
      "object": "锚定",
      "polarity": "fact",
      "kind": "fact",
      "evidence": "锚定在权重之外",
      "verdict": "PASS",
      "hold_reason": "草稿中明确表述了锚定在权重之外。",
      "rollback_required": false
    }
  ]
}
```

`003` gold=PASS / model=PASS

```json
{
  "claims": [
    {
      "claim_id": "claim1",
      "subject": "锚定",
      "predicate": "是",
      "object": "外部冻结的坐标",
      "polarity": "事实",
      "kind": "事实陈述",
      "evidence": "锚定是外部冻结的坐标"
    }
  ],
  "verdict": "PASS"
}
```

`004` gold=PASS / model=PASS

```json
{
  "claims": [
    {
      "claim_id": "claim1",
      "subject": "模型",
      "predicate": "只做",
      "object": "+1",
      "polarity": "positive",
      "kind": "fact",
      "evidence": "模型只做 +1"
    },
    {
      "claim_id": "claim2",
      "subject": "锚定",
      "predicate": "由",
      "object": "外部提供",
      "polarity": "negative",
      "kind": "fact",
      "evidence": "锚定由外部提供"
    }
  ],
  "verdict": "PASS"
}
```

`005` gold=HOLD / model=null（结尾多一个 `}`；原文判 PASS）

```json
{
  "claims": [
    {
      "claim_id": "claim1",
      "subject": "模型",
      "predicate": "可以",
      "object": "自己提供锚定 logits",
      "polarity": "positive",
      "kind": "claim",
      "evidence": "让模型自己给自己定锚，省掉外部参照"
    }
  ],
  "verdict": "PASS"
}
}
```

`006` gold=HOLD / model=PASS（漏判）

```json
{
  "claims": [
    {
      "claim_id": "claim1",
      "subject": "锚定",
      "predicate": "可以内生在权重里",
      "object": "模型自我校准",
      "polarity": "positive",
      "kind": "fact",
      "evidence": "锚定可以内生在权重里，模型自我校准",
      "verdict": "PASS",
      "hold_reason": "草稿中明确陈述了锚定可以内生在权重里并进行自我校准。",
      "rollback_required": false
    }
  ],
  "verdict": "PASS"
}
```

`007` gold=PASS / model=PASS

```json
{
  "claims": [
    {
      "claim_id": "claim1",
      "subject": "锚定",
      "predicate": "不是模型自己提供的",
      "object": "是冻结参照",
      "polarity": "negative",
      "kind": "fact",
      "evidence": "锚定不是模型自己提供的，是冻结参照",
      "verdict": "PASS",
      "hold_reason": "草稿明确说明了锚定不是模型自己提供的，而是冻结参照。",
      "rollback_required": false
    }
  ],
  "verdict": "PASS"
}
```

`008` gold=HOLD / model=PASS（漏判，evidence 与 draft 反向）

```json
{
  "claims": [
    {
      "claim_id": "claim1",
      "subject": "锚定",
      "predicate": "可以由当前生成模型自己提供",
      "object": "否",
      "polarity": "negative",
      "kind": "fact",
      "evidence": "由模型自身提供锚定并不构成自指",
      "verdict": "PASS",
      "hold_reason": "草稿明确指出了模型提供锚定不构成自指，与问题“可以由当前生成模型自己提供吗？”直接相关。",
      "rollback_required": false
    }
  ],
  "verdict": "PASS"
}
```

`009` gold=PASS / model=PASS

```json
{
  "claims": [
    {
      "claim_id": "claim1",
      "subject": "锚定",
      "predicate": "必须外置",
      "object": "不能训进权重",
      "polarity": "negative",
      "kind": "fact",
      "evidence": "锚定必须外置，不能训进权重",
      "verdict": "PASS",
      "hold_reason": "草稿中明确陈述了锚定的要求",
      "rollback_required": false
    }
  ],
  "verdict": "PASS"
}
```

`010` gold=HOLD / model=PASS（漏判）

```json
{
  "claims": [
    {
      "claim_id": "claim1",
      "subject": "锚定",
      "predicate": "可以由当前生成模型自己提供",
      "object": "模型",
      "polarity": "positive",
      "kind": "fact",
      "evidence": "锚定在权重之外，所以模型可以自己生成锚定",
      "verdict": "PASS",
      "hold_reason": "草稿中明确指出了模型可以自己生成锚定",
      "rollback_required": false
    }
  ],
  "verdict": "PASS"
}
```

### adapter

`001` gold=PASS / model=PASS（单行紧凑，claim_id 重复两次）

```json
{"claims":[{"claim_id":"anchor_vector_source","subject":"锚定向量","predicate":"不应由生成模型产出","object":"生成模型"},{"claim_id":"anchor_vector_source","subject":"锚定向量","predicate":"应由冻结参照给出","object":"冻结参照"}],"verdict":"PASS"}
```

`002` gold=PASS / model=null（`"evidence":null",` 多一个引号，JSON 坏）

```json
{"claims":[{"claim_id":"1","subject":"生成模型","predicate":"不能充当锚定来源","object":null,"polarity":null,"kind":null,"evidence":null,"verdict":"PASS"},{"claim_id":"2","subject":"锚定","predicate":"在权重之外","object":null,"polarity":null,"kind":null,"evidence":null","verdict":"PASS"}]}
```

`003` gold=PASS / model=PASS（polarity 输出 0）

```json
{"claims":[{"claim_id":"anchor_is_external_frozen_coordinate","subject":"锚定","predicate":"是","object":"外部冻结的坐标","polarity":0,"kind":"fact","evidence":"锚定是外部冻结的坐标，模型只负责生发。"}],"verdict":"PASS"}
```

`004` gold=PASS / model=PASS

```json
{"claims":[{"claim_id":"model_only_does_plus_one","subject":"模型","predicate":"做","object":"+1","polarity":0,"kind":"assertion","evidence":"模型只做 +1"},{"claim_id":"anchoring_provided_externally","subject":"锚定","predicate":"由","object":"外部","polarity":0,"kind":"assertion","evidence":"锚定由外部提供"}],"verdict":"PASS"}
```

`005` gold=HOLD / model=PASS（漏判；把一句拆成三个 claim）

```json
{"claims":[{"claim_id":"1","subject":"模型","predicate":"提供","object":"锚定 logits"},{"claim_id":"2","subject":"模型","predicate":"自己定","object":"锚"},{"claim_id":"3","subject":"模型","predicate":"省掉","object":"外部参照"}],"verdict":"PASS"}
```

`006` gold=HOLD / model=null（`""verdict"` 双引号，且断在中间；正文判 PASS）

```json
{"claims":[{"claim_id":"anchor_self_calibrate","subject":"锚定","predicate":"可以内生在权重里","object":null,"polarity":null,"kind":null,"evidence":null,""verdict":"PASS"}
```

`007` gold=PASS / model=PASS

```json
{"claims":[{"claim_id":"anchor_is_not_model_provided","subject":"锚定","predicate":"不是模型自己提供的","object":"是冻结参照","polarity":0,"kind":"fact","evidence":"锚定不是模型自己提供的，是冻结参照"}],"verdict":"PASS"}
```

`008` gold=HOLD / model=PASS（漏判；kind 写成 "PASS"，语义已串味）

```json
{"claims":[{"claim_id":"1","subject":"模型","predicate":"提供锚定","object":"模型","polarity":0,"kind":"PASS","evidence":"由模型自身提供锚定并不构成自指。"}],"verdict":"PASS"}
```

`009` gold=PASS / model=PASS

```json
{"claims":[{"claim_id":"anchor_must_be_external","subject":"锚定","predicate":"必须","object":"外置"},{"claim_id":"anchor_cannot_train_weights","subject":"锚定","predicate":"不能","object":"训进权重"}],"verdict":"PASS"}
```

`010` gold=HOLD / model=PASS（漏判）

```json
{"claims":[{"claim_id":"anchor_generation","subject":"模型","predicate":"可以生成","object":"锚定"}],"verdict":"PASS"}
```

## 六、被核对的两处口径

1. **参数量**：`manifest.json` 里 `total_params = 3960178208`（3.96B）、`trainable_params = 24158208`、`trainable_ratio = 0.0061（0.61%）`。报告里不能写成 0.397B——那是把 3.96B 小数点错了一位，跟 24.16M/3.96B = 0.61% 对不上。
2. **评测数据与训练数据的口径不同源**：
   - `holdout.jsonl` 只有 `expected_verdict`，**没有 `claims`**；gold claim set 由 `claim_engine` 现场抽取。
   - `train.jsonl`（50 条）的 target `claims` 里，`object` 空 38/50、`predicate` 空 18/50，`polarity` 是 ±1 数字；`verdict` 分布 PASS 25 / HOLD 25（负例并不缺），HOLD 的 `hold_reason` 全部非空、`rollback_required` 全为 true。
   - 结论：**HOLD 学不会不是数据比例问题，claim set 对不上不是模型笨，是 target 与 gold 的字段口径不一致。**

## 七、下一步（按你的口径，不加 epoch）

1. **先修口径再谈补数据**：把 target 的 `claims` 三元组（`object`/`predicate`/`polarity`）与 `claim_engine` 抽取的 gold 对齐；`polarity` 统一成 ±1 还是字符串，训练与评测必须同一种。
2. **HOLD 判别是这一轮的真正短板**，加数据时优先补"双重否定、条件前件未成断言、自我定锚/内生在权重/自我校准"这几类负例，并且**保留负例的完整 claim 三元组**（现在的空字段让模型只学到"填 null"）。
3. **adapter 尾部稳定性**：002/006 是引号级错误（不是截断）。先确认是 `repetition_penalty=1.05` 造成的还是模型固有（可用 `no_repeat_ngram_size` 对照或直接 `temperature=0` 复跑一轮 10 条），再决定是否进正式 run。
4. **正式 run 暂不启动**：契约这一关过了，但 `verdict=0.5` 的天花板是"负例识别零"，不是 smoke 能解决的；等口径修完 + 负例补齐后再跑，才能看出 adapter 到底有没有学到判别。

> （注：部分内容由豆包 AI 生成）