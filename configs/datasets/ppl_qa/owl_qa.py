from opencompass.openicl.icl_prompt_template import PromptTemplate
from opencompass.openicl.icl_retriever import FixKRetriever, ZeroRetriever
from opencompass.openicl.icl_inferencer import GenInferencer, SCInferencer, CoTInferencer, PPLQAInferencer
from opencompass.openicl.icl_evaluator import MeanEvaluator
from opencompass.utils.text_postprocessors import first_capital_postprocess_multi
from opencompass.datasets import QADataset
from mmengine.config import read_base

with read_base():
    from ...commons.prompts import prompts
    from ...paths import ROOT_DIR
import os

owl_qa_reader_cfg = dict(
    input_columns=['question', 'answer'],
    output_column='answer',
    train_split='dev'
)

owl_qa_eval_cfg = dict(
    evaluator=dict(type=MeanEvaluator, field_name='PPL'))

owl_ppl_qa_datasets = [
    dict(
        type=QADataset,
        abbr=f'owl_qa_{lang}-{shot_abbr}-ppl',
        path=f'{ROOT_DIR}data/opseval/owl/qa/', 
        name=f'owl_qa_{lang}',
        reader_cfg=owl_qa_reader_cfg,
        infer_cfg=dict(
            ice_template=dict(
                type=PromptTemplate,
                template=dict( 
                    round=[
                        dict(
                            role="HUMAN",
                            prompt=prompt_hint
                        ),
                        dict(role="BOT", prompt=f"{answer_hint}{{answer}}\n"),
                    ]
                ),
            ),
            prompt_template=dict(
                type=PromptTemplate,
                template=dict(
                    begin="</E>", 
                    round=[
                        dict(
                            role="HUMAN",
                            prompt=prompt_hint
                        ),
                        dict(role="BOT", prompt=f"{answer_hint}{{answer}}\n"),
                    ]
                ),
                ice_token="</E>",
            ),
            retriever=dict(type=retriever, **fixidlist),
            inferencer=dict(
                type=PPLQAInferencer,
                save_every=20
            ),
        ),
        eval_cfg=owl_qa_eval_cfg)
    for shot_abbr, fixidlist, shot_hint_id, retriever in zip(
            ['Zero-shot', '3-shot'],
            [dict(), dict(fix_id_list=[0,1,2])],
            [0, 1],
            [ZeroRetriever, FixKRetriever]
        )
    for lang, prompt_hint, answer_hint in zip(
        ['zh', 'en'],
        [
            f"你是一名运维专家，请用一句话回答下面这个问题：\n{{question}}\n",
            f"You are an IT operations expert, please answer the following question in one sentence: \n{{question}}\n"
        ],
        [
            '答案： ',
            'Answer: '
        ]
    )
]
