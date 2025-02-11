from opencompass.models import HuggingFace, HuggingFaceCausalLM


models = [
    dict(
        type=HuggingFaceCausalLM,
        abbr='xverse_13b',
        path="/mnt/mfs/opsgpt/models/xverse/XVERSE-13B",
        tokenizer_path='/mnt/mfs/opsgpt/models/xverse/XVERSE-13B',
        tokenizer_kwargs=dict(padding_side='left',
                              truncation_side='left',
                              trust_remote_code=True,
                              use_fast=False,),
        max_out_len=20,
        max_seq_len=2048,
        batch_size=16,
        model_kwargs=dict(device_map='auto', trust_remote_code=True),
        # generate_kwargs=dict(
        #     temperature=0
        # ), 
        run_cfg=dict(num_gpus=2, num_procs=1),
    )
]
