echo `date`, Setup the environment ...
set -e  # exit if error

cd /mnt/tenant-home_speed/lyh/OpenCompass-OpsQA-lyh
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 python run.py /mnt/tenant-home_speed/lyh/opseval-configs/zzr/runconfig.py -w /mnt/tenant-home_speed/lyh/outputs/xll/lora_rank_lab/ --mode infer -r