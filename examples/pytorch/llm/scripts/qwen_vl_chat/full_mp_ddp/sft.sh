# Experimental environment: 4 * A100
# 4 * 55GB GPU memory
NPROC_PER_NODE=2 \
CUDA_VISIBLE_DEVICES=0,1,2,3 \
swift sft \
    --model_type qwen-vl-chat \
    --sft_type full \
    --train_dataset_sample -1 \
    --eval_steps 100 \
    --output_dir output \
    --num_train_epochs 1 \
    --max_length 2048 \
    --learning_rate 2e-5 \
    --use_flash_attn true \
    --only_save_model true \
    --dataset coco-mini-en \
