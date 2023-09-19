from opencompass.models import HuggingFaceCausalLM

ROOT_DIR = '/mnt/mfs/opsgpt/'

_meta_template = dict(
    round=[
        dict(role="HUMAN", api_role="HUMAN"),
        dict(role="BOT", api_role="BOT", generate=True),
    ],
)

models = [
    dict(
        abbr="chinese-alpaca-2-13b",
        type=HuggingFaceCausalLM, 
        path=ROOT_DIR+"models/chinese-llama-2/chinese-alpaca-2-13b/",
        tokenizer_path=ROOT_DIR+"models/chinese-llama-2/chinese-alpaca-2-13b/",
        max_out_len=1024,
        max_seq_len=2048,
        batch_size=16,
        meta_template=_meta_template,
        model_kwargs=dict(device_map='auto', trust_remote_code=True),
        batch_padding=False,
        run_cfg=dict(num_gpus=4, num_procs=1),
    ),
]
