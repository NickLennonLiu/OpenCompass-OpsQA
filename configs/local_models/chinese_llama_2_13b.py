from opencompass.models import HuggingFaceCausalLM


models = [
    dict(
        abbr="chinese-llama-2-13b",
        type=HuggingFaceCausalLM, 
        path="/gpudata/home/cbh/opsgpt//models/chinese-llama-2/chinese-llama-2-13b/",
        tokenizer_path="/gpudata/home/cbh/opsgpt/models/chinese-llama-2/chinese-llama-2-13b/",
        tokenizer_kwargs=dict(padding_side='left',
                              truncation_side='left',
                              use_fast=False,
                              ),
        max_out_len=1024,
        max_seq_len=2048,
        batch_size=16,
        model_kwargs=dict(device_map='auto', trust_remote_code=True),
        batch_padding=False,
        run_cfg=dict(num_gpus=4, num_procs=1),
    ),
]
