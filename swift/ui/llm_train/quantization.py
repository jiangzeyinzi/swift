from typing import Type

import gradio as gr

from swift.ui.base import BaseUI


class Quantization(BaseUI):

    group = 'llm_train'

    locale_dict = {
        'quantization_tab': {
            'label': {
                'zh': '量化参数',
                'en': 'Quantization'
            },
        },
        'quantization_bit': {
            'label': {
                'zh': '量化bit数',
                'en': 'Quantization bit'
            },
            'info': {
                'zh': '设置量化bit数, 0代表不进行量化',
                'en': 'Set the quantization bit, 0 for no quantization'
            }
        },
        'bnb_4bit_comp_dtype': {
            'label': {
                'zh': 'bnb_4bit_comp_dtype',
                'en': 'bnb_4bit_comp_dtype'
            },
        },
        'bnb_4bit_quant_type': {
            'label': {
                'zh': 'bnb_4bit_quant_type',
                'en': 'bnb_4bit_quant_type'
            },
        },
        'bnb_4bit_use_double_quant': {
            'label': {
                'zh': 'bnb_4bit_use_double_quant',
                'en': 'bnb_4bit_use_double_quant'
            },
        },
    }

    @classmethod
    def do_build_ui(cls, base_tab: Type['BaseUI']):
        with gr.Accordion(elem_id='quantization_tab', open=False):
            with gr.Row():
                gr.Slider(
                    elem_id='quantization_bit', minimum=0, maximum=8, step=4)
                gr.Dropdown(elem_id='bnb_4bit_comp_dtype')
                gr.Dropdown(elem_id='bnb_4bit_quant_type')
                gr.Checkbox(elem_id='bnb_4bit_use_double_quant')
