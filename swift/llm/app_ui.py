# Copyright (c) Alibaba, Inc. and its affiliates.
from typing import Tuple

from .infer import merge_lora, prepare_model_template
from .utils import (History, InferArguments, inference_stream,
                    limit_history_length)


def clear_session() -> History:
    return []


def gradio_generation_demo(args: InferArguments) -> None:
    import gradio as gr
    if args.infer_backend == 'vllm':
        from swift.llm import prepare_vllm_engine_template, inference_stream_vllm, inference_vllm
        llm_engine, template = prepare_vllm_engine_template(args)
    else:
        model, template = prepare_model_template(args)

    def model_generation(query: str) -> str:
        if args.infer_backend == 'vllm':
            gen = inference_stream_vllm(llm_engine, template, [{
                'query': query
            }])
            for resp_list in gen:
                response = resp_list[0]['response']
                yield response
        else:
            gen = inference_stream(model, template, query, None)
            for response, _ in gen:
                yield response

    model_name = args.model_type.title()

    with gr.Blocks() as demo:
        gr.Markdown(f'<center><font size=8>{model_name} Bot</center>')
        with gr.Row():
            with gr.Column(scale=1):
                input_box = gr.Textbox(lines=16, label='Input', max_lines=16)
            with gr.Column(scale=1):
                output_box = gr.Textbox(lines=16, label='Output', max_lines=16)
        send = gr.Button('🚀 发送')
        send.click(model_generation, inputs=[input_box], outputs=[output_box])
    demo.queue().launch(height=1000, share=args.share)


def gradio_chat_demo(args: InferArguments) -> None:
    import gradio as gr
    if args.infer_backend == 'vllm':
        from swift.llm import prepare_vllm_engine_template, inference_stream_vllm
        llm_engine, template = prepare_vllm_engine_template(args)
    else:
        model, template = prepare_model_template(args)

    def model_chat(query: str, history: History) -> Tuple[str, History]:
        old_history, history = limit_history_length(template, query, history,
                                                    args.max_length)
        if args.infer_backend == 'vllm':
            gen = inference_stream_vllm(llm_engine, template,
                                        [{
                                            'query': query,
                                            'history': history
                                        }])
            for resp_list in gen:
                history = resp_list[0]['history']
                total_history = old_history + history
                yield '', total_history
        else:
            gen = inference_stream(model, template, query, history)
            for _, history in gen:
                total_history = old_history + history
                yield '', total_history

    model_name = args.model_type.title()
    with gr.Blocks() as demo:
        gr.Markdown(f'<center><font size=8>{model_name} Bot</center>')

        chatbot = gr.Chatbot(label=f'{model_name}')
        message = gr.Textbox(lines=2, label='Input')
        with gr.Row():
            clear_history = gr.Button('🧹 清除历史对话')
            send = gr.Button('🚀 发送')
        send.click(
            model_chat, inputs=[message, chatbot], outputs=[message, chatbot])
        clear_history.click(
            fn=clear_session, inputs=[], outputs=[chatbot], queue=False)
    demo.queue().launch(height=1000, share=args.share)


def llm_app_ui(args: InferArguments) -> None:
    args.eval_human = True
    if args.merge_lora_and_save:
        merge_lora(args, device_map='cpu')
    if args.template_type.endswith('generation'):
        gradio_generation_demo(args)
    else:
        gradio_chat_demo(args)
