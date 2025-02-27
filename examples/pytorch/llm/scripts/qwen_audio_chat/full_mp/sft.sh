# Experimental environment: 2 * A100
# 2 * 50GB GPU memory
CUDA_VISIBLE_DEVICES=0,1 \
swift sft \
    --model_type qwen-audio-chat \
    --sft_type full \
    --train_dataset_sample -1 \
    --eval_steps 100 \
    --output_dir output \
    --num_train_epochs 1 \
    --max_length 2048 \
    --learning_rate 2e-5 \
    --use_flash_attn true \
    --only_save_model true \
    --dataset aishell1-mini-zh \
    --lazy_tokenize true \
