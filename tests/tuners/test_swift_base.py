import copy
import math
import os
import shutil
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

import torch
from modelscope import Model, Preprocessor
from modelscope.models.nlp.structbert import (SbertConfig,
                                              SbertForSequenceClassification)
from peft.utils import WEIGHTS_NAME
from torch import nn

from swift import (AdapterConfig, LoRAConfig, PromptConfig, ResTuningConfig,
                   SideConfig, Swift, SwiftModel)


class TestSwift(unittest.TestCase):

    def setUp(self):
        print(('Testing %s.%s' % (type(self).__name__, self._testMethodName)))
        self.tmp_dir = tempfile.TemporaryDirectory().name
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)
        super().tearDown()

    def test_swift_lora_forward(self):

        from swift.tuners.lora import Linear

        def reset_lora_parameters(self, adapter_name, init_lora_weights):
            if init_lora_weights is False:
                return

            if adapter_name in self.lora_A.keys():
                if init_lora_weights is True:
                    # initialize A the same way as the default for nn.Linear and B to zero
                    # https://github.com/microsoft/LoRA/blob/a0a92e0f26c067cf94747bdbf1ce73793fa44d19/loralib/layers.py#L124
                    nn.init.kaiming_uniform_(
                        self.lora_A[adapter_name].weight, a=math.sqrt(5))
                elif init_lora_weights.lower() == 'gaussian':
                    nn.init.normal_(
                        self.lora_A[adapter_name].weight,
                        std=1 / self.r[adapter_name])
                else:
                    raise ValueError(
                        f'Unknown initialization {init_lora_weights=}')
                nn.init.ones_(self.lora_B[adapter_name].weight)
            if adapter_name in self.lora_embedding_A.keys():
                # initialize a the same way as the default for nn.linear and b to zero
                nn.init.ones_(self.lora_embedding_A[adapter_name])
                nn.init.normal_(self.lora_embedding_B[adapter_name])

        Linear.reset_lora_parameters = reset_lora_parameters

        model = Model.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        preprocessor = Preprocessor.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        inputs = preprocessor('how are you')
        lora_config = LoRAConfig(target_modules=['query', 'key', 'value'])
        outputs = model(**inputs)
        model = Swift.prepare_model(model, config=lora_config)
        model.eval()
        outputs_lora = model(**inputs)
        model.deactivate_adapter('default')
        outputs_deactivate = model(**inputs)
        model.activate_adapter('default')
        outputs_reactivate = model(**inputs)
        self.assertTrue(
            torch.allclose(outputs.logits, outputs_deactivate.logits))
        self.assertTrue(
            not torch.allclose(outputs.logits, outputs_lora.logits))
        self.assertTrue(
            torch.allclose(outputs_lora.logits, outputs_reactivate.logits))

    def test_swift_adapter_forward(self):
        model = Model.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        preprocessor = Preprocessor.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        inputs = preprocessor('how are you')
        adapter_config = AdapterConfig(
            dim=model.config.hidden_size,
            target_modules=r'.*layer\.\d+$',
            method_name='feed_forward_chunk',
            hidden_pos=0)
        outputs = model(**inputs)
        model = Swift.prepare_model(model, config=adapter_config)
        outputs_lora = model(**inputs)
        model.deactivate_adapter('default')
        outputs_deactivate = model(**inputs)
        model.activate_adapter('default')
        outputs_reactivate = model(**inputs)
        self.assertTrue(
            torch.allclose(outputs.logits, outputs_deactivate.logits))
        self.assertTrue(
            not torch.allclose(outputs.logits, outputs_lora.logits))
        self.assertTrue(
            torch.allclose(outputs_lora.logits, outputs_reactivate.logits))

    def test_swift_prompt_forward(self):
        model = Model.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        preprocessor = Preprocessor.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        inputs = preprocessor('how are you')
        prompt_config = PromptConfig(
            dim=model.config.hidden_size,
            target_modules=r'.*layer\.\d+$',
            embedding_pos=0,
            attention_mask_pos=1)
        outputs = model(**inputs)
        model = Swift.prepare_model(model, config=prompt_config)
        outputs_lora = model(**inputs)
        model.deactivate_adapter('default')
        outputs_deactivate = model(**inputs)
        model.activate_adapter('default')
        outputs_reactivate = model(**inputs)
        self.assertTrue(
            torch.allclose(outputs.logits, outputs_deactivate.logits))
        self.assertTrue(
            not torch.allclose(outputs.logits, outputs_lora.logits))
        self.assertTrue(
            torch.allclose(outputs_lora.logits, outputs_reactivate.logits))

    def test_swift_restuner_forward(self):
        model = Model.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        preprocessor = Preprocessor.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        inputs = preprocessor('how are you')
        restuner_config = ResTuningConfig(
            dims=model.config.hidden_size,
            root_modules=r'.*layer.0$',
            stem_modules=r'.*layer\.\d+$',
            target_modules=r'.*pooler',
            target_modules_hook='input',
            tuner_cfg='res_adapter',
        )
        outputs = model(**inputs)
        model = Swift.prepare_model(model, config=restuner_config)
        outputs_lora = model(**inputs)
        model.deactivate_adapter('default')
        outputs_deactivate = model(**inputs)
        model.activate_adapter('default')
        outputs_reactivate = model(**inputs)
        self.assertTrue(
            torch.allclose(outputs.logits, outputs_deactivate.logits))
        self.assertTrue(
            not torch.allclose(outputs.logits, outputs_lora.logits))
        self.assertTrue(
            torch.allclose(outputs_lora.logits, outputs_reactivate.logits))

    def lora_injection_with_dtype(self, dtype=torch.float32):
        from swift.tuners.lora import Linear

        def reset_lora_parameters(self, adapter_name, init_lora_weights):
            if init_lora_weights is False:
                return

            if adapter_name in self.lora_A.keys():
                if init_lora_weights is True:
                    nn.init.kaiming_uniform_(
                        self.lora_A[adapter_name].weight, a=math.sqrt(5))
                elif init_lora_weights.lower() == 'gaussian':
                    nn.init.normal_(
                        self.lora_A[adapter_name].weight,
                        std=1 / self.r[adapter_name])
                else:
                    raise ValueError(
                        f'Unknown initialization {init_lora_weights=}')
                nn.init.ones_(self.lora_B[adapter_name].weight)
            if adapter_name in self.lora_embedding_A.keys():
                # initialize a the same way as the default for nn.linear and b to zero
                nn.init.ones_(self.lora_embedding_A[adapter_name])
                nn.init.normal_(self.lora_embedding_B[adapter_name])

        Linear.reset_lora_parameters = reset_lora_parameters

        model = Model.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        preprocessor = Preprocessor.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        input = preprocessor('this is a test')
        model = model.to(dtype)
        model2 = Model.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        model2 = model2.to(dtype)
        lora_config = LoRAConfig(target_modules=['query', 'key', 'value'])
        model = Swift.prepare_model(model, config=lora_config)
        self.assertTrue(isinstance(model, SwiftModel))
        output1 = model(**input)
        model.save_pretrained(self.tmp_dir)
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, 'default')))
        self.assertTrue(
            os.path.exists(
                os.path.join(self.tmp_dir, 'default', WEIGHTS_NAME)))

        model2 = Swift.from_pretrained(model2, self.tmp_dir)
        output2 = model2(**input)
        self.assertTrue(torch.allclose(output1.logits, output2.logits))
        state_dict = model.state_dict()
        state_dict2 = model2.state_dict()
        for key in state_dict:
            self.assertTrue(key in state_dict2)
            self.assertTrue(
                all(
                    torch.isclose(state_dict[key],
                                  state_dict2[key]).flatten().detach().cpu()))

        if dtype == torch.float32 and os.environ.get(
                'USE_UNIQUE_THREAD') == '1':
            Swift.merge_and_unload(model2)
            output3 = model2(**input)
            self.assertTrue(torch.allclose(output1.logits, output3.logits))

    def test_swift_lora_injection(self):
        self.lora_injection_with_dtype()

    def test_swift_lora_injection_bf16(self):
        self.lora_injection_with_dtype(torch.bfloat16)

    def test_swift_multiple_adapters(self):
        model = SbertForSequenceClassification(SbertConfig())
        model2 = copy.deepcopy(model)
        lora_config = LoRAConfig(target_modules=['query', 'key', 'value'])
        adapter_config = AdapterConfig(
            dim=model.config.hidden_size,
            target_modules=r'.*layer\.\d+$',
            method_name='feed_forward_chunk',
            hidden_pos=0)
        model = Swift.prepare_model(
            model, config={
                'lora': lora_config,
                'adapter': adapter_config
            })
        self.assertTrue(isinstance(model, SwiftModel))
        model.save_pretrained(self.tmp_dir, adapter_name=['lora', 'adapter'])
        with open(os.path.join(self.tmp_dir, 'configuration.json'), 'w') as f:
            f.write('{}')
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, 'lora')))
        self.assertTrue(
            os.path.exists(os.path.join(self.tmp_dir, 'lora', WEIGHTS_NAME)))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, 'adapter')))
        self.assertTrue(
            os.path.exists(
                os.path.join(self.tmp_dir, 'adapter', WEIGHTS_NAME)))
        model2 = Swift.from_pretrained(
            model2, self.tmp_dir, adapter_name=['lora', 'adapter'])
        state_dict = model.state_dict()
        state_dict2 = model2.state_dict()
        for key in state_dict:
            self.assertTrue(key in state_dict2)
            self.assertTrue(
                all(
                    torch.isclose(state_dict[key],
                                  state_dict2[key]).flatten().detach().cpu()))

    def test_swift_multiple_adapters_switching(self):
        from swift.tuners.lora import Linear
        from swift.tuners.adapter import AdapterModule

        def reset_lora_parameters(self, adapter_name, init_lora_weights):
            if init_lora_weights is False:
                return

            if adapter_name in self.lora_A.keys():
                if init_lora_weights is True:
                    # initialize A the same way as the default for nn.Linear and B to zero
                    # https://github.com/microsoft/LoRA/blob/a0a92e0f26c067cf94747bdbf1ce73793fa44d19/loralib/layers.py#L124
                    nn.init.ones_(self.lora_A[adapter_name].weight)
                elif init_lora_weights.lower() == 'gaussian':
                    nn.init.normal_(
                        self.lora_A[adapter_name].weight,
                        std=1 / self.r[adapter_name])
                else:
                    raise ValueError(
                        f'Unknown initialization {init_lora_weights=}')
                nn.init.ones_(self.lora_B[adapter_name].weight)
            if adapter_name in self.lora_embedding_A.keys():
                # initialize a the same way as the default for nn.linear and b to zero
                nn.init.ones_(self.lora_embedding_A[adapter_name])
                nn.init.normal_(self.lora_embedding_B[adapter_name])

        Linear.reset_lora_parameters = reset_lora_parameters

        def init_weights(self):

            def _init_weights(m):
                if isinstance(m, nn.Linear):
                    nn.init.ones_(m.weight)
                    nn.init.ones_(m.bias)

            self.apply(_init_weights)

        AdapterModule.init_weights = init_weights

        model = Model.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        preprocessor = Preprocessor.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        inputs = preprocessor('how are you')
        model1 = copy.deepcopy(model)
        model2 = copy.deepcopy(model)
        model1 = Swift.prepare_model(
            model1,
            config={
                'lora1':
                LoRAConfig(target_modules=['query', 'key', 'value']),
                'adapter1':
                AdapterConfig(
                    dim=model.config.hidden_size,
                    target_modules=r'.*layer\.\d+$',
                    method_name='feed_forward_chunk',
                    hidden_pos=0)
            })
        model2 = Swift.prepare_model(
            model2,
            config={
                'lora2':
                LoRAConfig(target_modules=['query', 'key', 'value']),
                'adapter2':
                AdapterConfig(
                    dim=model.config.hidden_size,
                    target_modules=r'.*layer\.\d+$',
                    method_name='feed_forward_chunk',
                    hidden_pos=0)
            })
        model = Swift.prepare_model(
            model,
            config={
                'lora1': LoRAConfig(target_modules=['query', 'key', 'value']),
                'lora2': LoRAConfig(target_modules=['query', 'key', 'value']),
            })

        model = Swift.prepare_model(
            model,
            config={
                'adapter1':
                AdapterConfig(
                    dim=model.config.hidden_size,
                    target_modules=r'.*layer\.\d+$',
                    method_name='feed_forward_chunk',
                    hidden_pos=0),
                'adapter2':
                AdapterConfig(
                    dim=model.config.hidden_size,
                    target_modules=r'.*layer\.\d+$',
                    method_name='feed_forward_chunk',
                    hidden_pos=0),
            })

        model.deactivate_adapter('adapter2')
        model.deactivate_adapter('lora2')
        outputs1 = model(**inputs)
        outputs2 = model1(**inputs)
        self.assertTrue(torch.allclose(outputs1.logits, outputs2.logits))
        model.activate_adapter('adapter2')
        model.activate_adapter('lora2')
        model.deactivate_adapter('adapter1')
        model.deactivate_adapter('lora1')
        outputs1 = model(**inputs)
        outputs2 = model2(**inputs)
        self.assertTrue(torch.allclose(outputs1.logits, outputs2.logits))

        if os.environ.get('USE_UNIQUE_THREAD') == '0':

            def thread_func1():
                model1.set_active_adapters(['lora1', 'adapter1'])
                model.set_active_adapters(['lora1', 'adapter1'])
                outputs_single = model1(**inputs)
                outputs_t1 = model(**inputs)
                self.assertTrue(
                    torch.allclose(outputs_single.logits, outputs_t1.logits))

            def thread_func2():
                model2.set_active_adapters(['lora2', 'adapter2'])
                model.set_active_adapters(['lora2', 'adapter2'])
                outputs_single = model2(**inputs)
                outputs_t2 = model(**inputs)
                self.assertTrue(
                    torch.allclose(outputs_single.logits, outputs_t2.logits))

            with ThreadPoolExecutor(2) as executor:
                f1 = executor.submit(thread_func1)
                f2 = executor.submit(thread_func2)
                e1 = f1.exception()
                e2 = f2.exception()
                if e1 is not None:
                    raise e1
                if e2 is not None:
                    raise e2

    def test_swift_side_bert(self):
        model = Model.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        preprocessor = Preprocessor.from_pretrained(
            'damo/nlp_structbert_sentence-similarity_chinese-base')
        inputs = preprocessor('how are you')
        model2 = copy.deepcopy(model)
        result_origin = model(**inputs).logits
        print(
            f'test_swift_side_bert result_origin shape: {result_origin.shape}, '
            f'result_origin sum: {torch.sum(result_origin)}')

        side_config = SideConfig(
            dim=model.config.hidden_size,
            target_modules=r'.*encoder.encoder',
            side_module_name='mlp',
            target_hidden_pos='last_hidden_state')

        model = Swift.prepare_model(model, config=side_config)
        result_activate = model(**inputs).logits
        model.deactivate_adapter('default')
        result_deactivate = model(**inputs).logits
        model.activate_adapter('default')
        result_reactivate = model(**inputs).logits
        self.assertTrue(torch.allclose(result_origin, result_deactivate))
        self.assertTrue(not torch.allclose(result_origin, result_activate))
        self.assertTrue(torch.allclose(result_activate, result_reactivate))
        print(
            f'test_swift_side_bert result shape: {result_origin.shape}, result sum: {torch.sum(result_origin)}'
        )

        self.assertTrue(isinstance(model, SwiftModel))
        model.save_pretrained(self.tmp_dir)
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, 'default')))
        self.assertTrue(
            os.path.exists(
                os.path.join(self.tmp_dir, 'default', WEIGHTS_NAME)))

        model2 = Swift.from_pretrained(model2, self.tmp_dir)

        state_dict = model.state_dict()
        state_dict2 = model2.state_dict()
        for key in state_dict:
            self.assertTrue(key in state_dict2)
            self.assertTrue(
                all(
                    torch.isclose(state_dict[key],
                                  state_dict2[key]).flatten().detach().cpu()))


if __name__ == '__main__':
    unittest.main()
