from opencompass.multimodal.models.qwen import QwenVLChatVQAPromptConstructor

# dataloader settings
val_pipeline = [
    dict(type='mmpretrain.LoadImageFromFile'),
    dict(type='mmpretrain.ToPIL', to_rgb=True),
    dict(type='mmpretrain.torchvision/Resize',
         size=(448, 448),
         interpolation=3),
    dict(type='mmpretrain.torchvision/ToTensor'),
    dict(type='mmpretrain.torchvision/Normalize',
         mean=(0.48145466, 0.4578275, 0.40821073),
         std=(0.26862954, 0.26130258, 0.27577711)),
    dict(
        type='mmpretrain.PackInputs',
        algorithm_keys=['question', 'gt_answer', 'gt_answer_weight'],
        meta_keys=['question_id', 'image_id'],
    )
]

dataset = dict(type='mmpretrain.OCRVQA',
               data_root='data/ocrvqa',
               ann_file='annotations/dataset.json',
               split='test',
               data_prefix='images',
               pipeline=val_pipeline)

qwen_ocrvqa_dataloader = dict(batch_size=1,
                  num_workers=4,
                  dataset=dataset,
                  collate_fn=dict(type='pseudo_collate'),
                  sampler=dict(type='DefaultSampler', shuffle=False))

# model settings
qwen_ocrvqa_model = dict(
    type='qwen-vl-chat',
    pretrained_path='Qwen/Qwen-VL-Chat',  # or Huggingface repo id
    prompt_constructor=dict(type=QwenVLChatVQAPromptConstructor)
)

# evaluation settings
qwen_ocrvqa_evaluator = [dict(type='mmpretrain.VQAAcc')]
