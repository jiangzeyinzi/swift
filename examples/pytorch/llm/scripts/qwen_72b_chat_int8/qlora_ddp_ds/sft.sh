# Experimental environment: 2 * A100
# 2 * 80GB GPU memory
nproc_per_node=2

PYTHONPATH=../../.. \
CUDA_VISIBLE_DEVICES=0,1 \
torchrun \
    --nproc_per_node=$nproc_per_node \
    --master_port 29500 \
    llm_sft.py \
    --model_type qwen-72b-chat-int8 \
    --model_revision master \
    --sft_type lora \
    --tuner_backend swift \
    --template_type AUTO \
    --dtype AUTO \
    --output_dir output \
    --ddp_backend nccl \
    --dataset codefuse-python-en \
    --train_dataset_sample -1 \
    --num_train_epochs 1 \
    --max_length 1024 \
    --truncation_strategy delete \
    --check_dataset_strategy warning \
    --lora_rank 8 \
    --lora_alpha 32 \
    --lora_dropout_p 0.05 \
    --lora_target_modules DEFAULT \
    --gradient_checkpointing true \
    --batch_size 1 \
    --weight_decay 0.01 \
    --learning_rate 1e-4 \
    --gradient_accumulation_steps $(expr 16 / $nproc_per_node) \
    --max_grad_norm 0.5 \
    --warmup_ratio 0.03 \
    --eval_steps 100 \
    --save_steps 100 \
    --save_total_limit 2 \
    --logging_steps 10 \
    --use_flash_attn true \
    --push_to_hub false \
    --push_hub_strategy end \
    --hub_model_id qwen-72b-chat-int8-qlora \
    --hub_private_repo true \
    --hub_token 'your-sdk-token' \
    --deepspeed_config_path 'ds_config/zero2.json' \
    --only_save_model true \
