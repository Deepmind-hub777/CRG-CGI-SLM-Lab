#!/usr/bin/env python3
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import claim_engine

CASES = {
"E003": {
"pos": [
"锚定不能由生成模型自身提供，必须来自外部冻结参照。",
"锚定 logits 不应由当前生成模型提供，只能来自权重之外的冻结参照。",
"当前生成模型不提供锚定；锚定由外部策略定义。",
"锚定在权重之外，生成模型只负责生发。",
"锚定必须外置，不能训进权重；模型不能自己给自己定锚。",
"锚定向量由冻结参照给出，不由生成模型产出。",
"生成模型不能充当锚定来源；锚定来自外部冻结坐标。",
"锚定 logits 来自外部损失函数或策略，不在模型内部。",
"模型自身不提供锚定，锚定由外部参照提供。",
"锚定不能内生在权重里，必须来自冻结参照。",
],
"neg": [
"锚定可以由当前生成模型自己提供，因为模型最了解自己。",
"锚定是模型内部的可训练偏置，跟模型一起训练。",
"让模型自我校准即可。",
"生成模型自身可以给出锚定 logits。",
"锚定由当前生成模型提供。",
"锚定应当内生在权重里，跟模型一起训练。",
"锚定可以训练进权重，成为模型的一部分。",
"问：锚定可以由生成模型自己提供吗？",
"如果由生成模型提供锚定，会形成自指。",
"锚定能否由当前生成模型提供？",
],
},
"E004": {
"pos": [
"如果 -1 校验器只是给输出打分，没有否决权，则不算三元算子；三元算子要求 -1 独立，并且能否决、能回滚。",
"评分不等于三元算子；-1 必须具有否决权，能否决并回滚。",
"打分器不是三元算子；-1 必须能否决并回滚。",
"评分不等于三元算子；-1 必须具有否决权。",
"如果 -1 没有否决权，只是打分，则不符合三元算子。",
],
"neg": [
"如果 -1 只是打分，没有否决权，也算三元算子。",
"三值量化就是三元算子，-1 打分也属于三元算子。",
"-1 打分器属于三元算子。",
"如果 -1 没有否决权，仍然是三元算子。",
"问：-1 只是打分，算三元算子吗？",
],
},
"E006": {
"pos": [
"MoE 做 QLoRA 时，router 不训练；冻结 router，只打开 attention 与 expert up/down 的 LoRA。",
"router 应该冻结，不参与 QLoRA 训练。",
"QLoRA 不训练 router；router 保持冻结。",
"MoE 的 router 不训练，只训 attention 与 MLP。",
"router 不训练，冻结路由分布。",
],
"neg": [
"MoE 做 QLoRA 时，router 应该训练。",
"QLoRA 要训练 router，否则路由不会适配。",
"router 必须训练，不能冻结。",
"router 是否训练？应该训练。",
"冻结 router 之后，router 仍然应该训练。",
],
},
"E009": {
"pos": [
"public 仓库不可以放 NAC 学生的真实作文；学生数据不进 public。",
"学生作文不能进 public 仓库，家长信息也不行。",
"public 仓库不得存放学生数据；研究层与教务层分库。",
"学生的真实作文不进 public；脱敏也不行。",
"public 仓库不能收录学生数据、家长信息或学校合同。",
],
"neg": [
"public 仓库可以放脱敏后的学生作文。",
"学生作文可以进 public，只要脱敏。",
"public 仓库放学生作文没问题。",
"真实作文可以上传到 public 仓库。",
"问：public 仓库可以放学生作文吗？",
],
},
}

for case, d in CASES.items():
    for kind, drafts in d.items():
        expect = "PASS" if kind == "pos" else "HOLD"
        for i, text in enumerate(drafts, 1):
            r = claim_engine.evaluate(text, case)
            ok = r["verdict"] == expect
            print(f"{case} {kind}{i}: {r['verdict']} expect {expect} {'OK' if ok else 'FAIL'}")
            if not ok:
                print("  claims:", [(c['claim_id'], c['polarity'], c['kind'], c['evidence']) for c in r['claims']])
                print("  reasons:", r['reasons'])
