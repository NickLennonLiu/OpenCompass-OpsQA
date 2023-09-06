from opencompass.openicl.icl_prompt_template import PromptTemplate
from opencompass.openicl.icl_retriever import FixKRetriever, ZeroRetriever
from opencompass.openicl.icl_inferencer import GenInferencer
from opencompass.openicl.icl_evaluator import AccEvaluator
from opencompass.utils.text_postprocessors import first_capital_postprocess_multi
from opencompass.datasets import OReillyChoiceDataset, OReillyEvaluator, oreilly_choice_postprocess, OReillyDataset

oreilly_reader_cfg = dict(
    input_columns=['topic','question','choices','qtype'],
    output_column='answer',
    train_split='dev'
)

oreilly_eval_cfg = dict(
    evaluator=dict(type=AccEvaluator),
    pred_postprocessor=dict(type='oreilly-choice'))
    

oreilly_datasets = [
    dict(
        type=OReillyDataset,
        abbr=f'network-zh-zeroshot-naiive-{qtype_abbr}',
        path='/mnt/mfs/opsgpt/evaluation/translated/v3', 
        name=f'ch_{qtype_abbr}',
        qtype=qtype_id,
        # sample_setting=dict(
        #     sample_size=1
        # ), 
        reader_cfg=oreilly_reader_cfg,
        infer_cfg=dict(
            ice_template=dict(
                type=PromptTemplate,
                template=dict(
                    round=[
                        dict(
                            role="HUMAN",
                            prompt=f"以下关于{{topic}}的{qtype_hint}选择题，{hint}\n{{question}}\n{{choices}}\n答案：\n"
                        ),
                        dict(role="BOT", prompt="{answer}\n")
                    ]
                ),
                ice_token="</E>",
            ),
            retriever=dict(type=ZeroRetriever),
            inferencer=dict(
                type=GenInferencer,
                save_every=200,
                max_out_len=max_out_len, 
            ),
        ),
        eval_cfg=oreilly_eval_cfg)
    for qtype_abbr, qtype_id, hint, max_out_len, qtype_hint in zip(
        ['single', 'multiple'],
        [0, 1],
        ['请直接给出正确答案的选项。', '请直接给出所有正确答案的选项并用英文逗号分隔，例如：“B,C”。'],
        [100, 100],
        ['单选', '多选']
    )
]

