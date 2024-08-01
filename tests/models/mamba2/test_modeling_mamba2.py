# coding=utf-8
# Copyright 2024 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import unittest

from parameterized import parameterized

from transformers import AutoTokenizer, Mamba2Config, is_torch_available
from transformers.testing_utils import require_torch, require_torch_gpu, slow, torch_device

from ...generation.test_utils import GenerationTesterMixin
from ...test_configuration_common import ConfigTester
from ...test_modeling_common import ModelTesterMixin, ids_tensor
from ...test_pipeline_mixin import PipelineTesterMixin


if is_torch_available():
    import torch

    from transformers import (
        Mamba2ForCausalLM,
        Mamba2Model,
    )
    from transformers.pytorch_utils import is_torch_greater_or_equal_than_2_0
else:
    is_torch_greater_or_equal_than_2_0 = False


class Mamba2ModelTester:
    config_classs = Mamba2Config
    model_class = Mamba2Model
    for_causal_lm = Mamba2ForCausalLM

    def __init__(
        self,
        parent,
        batch_size=14,
        num_heads=8,
        n_groups=8,
        state_size=2,
        head_dim=8,
        conv_kernel=4,
        chunk_size=8,
        seq_length=7,
        is_training=True,
        use_labels=True,
        vocab_size=99,
        hidden_size=32,
        num_hidden_layers=2,
        hidden_act="silu",
        hidden_dropout_prob=0.1,
        max_position_embeddings=512,
        type_vocab_size=16,
        type_sequence_label_size=2,
        num_labels=3,
        num_choices=4,
        scope=None,
        tie_word_embeddings=False,
    ):
        self.parent = parent
        self.num_heads = num_heads
        self.n_groups = n_groups
        self.head_dim = head_dim
        self.state_size = state_size
        self.conv_kernel = conv_kernel
        self.chunk_size = chunk_size
        self.batch_size = batch_size
        self.seq_length = seq_length
        self.is_training = is_training
        self.use_labels = use_labels
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        self.num_hidden_layers = num_hidden_layers
        self.hidden_act = hidden_act
        self.hidden_dropout_prob = hidden_dropout_prob
        self.max_position_embeddings = max_position_embeddings
        self.type_vocab_size = type_vocab_size
        self.type_sequence_label_size = type_sequence_label_size
        self.num_labels = num_labels
        self.num_choices = num_choices
        self.scope = scope
        self.bos_token_id = vocab_size - 1
        self.eos_token_id = vocab_size - 1
        self.pad_token_id = vocab_size - 1
        self.tie_word_embeddings = tie_word_embeddings

    def get_large_model_config(self):
        return Mamba2Config.from_pretrained("Molbap/code2")

    def prepare_config_and_inputs(
        self, gradient_checkpointing=False, scale_attn_by_inverse_layer_idx=False, reorder_and_upcast_attn=False
    ):
        input_ids = ids_tensor([self.batch_size, self.seq_length], self.vocab_size)

        sequence_labels = None
        token_labels = None
        choice_labels = None
        if self.use_labels:
            sequence_labels = ids_tensor([self.batch_size], self.type_sequence_label_size)
            token_labels = ids_tensor([self.batch_size, self.seq_length], self.num_labels)
            choice_labels = ids_tensor([self.batch_size], self.num_choices)

        config = self.get_config(
            gradient_checkpointing=gradient_checkpointing,
        )

        return (
            config,
            input_ids,
            None,
            sequence_labels,
            token_labels,
            choice_labels,
        )

    def get_config(self, gradient_checkpointing=False):
        return Mamba2Config(
            head_dim=self.head_dim,
            num_heads=self.num_heads,
            n_groups=self.n_groups,
            state_size=self.state_size,
            conv_kernel=self.conv_kernel,
            chunk_size=self.chunk_size,
            vocab_size=self.vocab_size,
            hidden_size=self.hidden_size,
            num_hidden_layers=self.num_hidden_layers,
            activation_function=self.hidden_act,
            n_positions=self.max_position_embeddings,
            type_vocab_size=self.type_vocab_size,
            use_cache=True,
            bos_token_id=self.bos_token_id,
            eos_token_id=self.eos_token_id,
            pad_token_id=self.pad_token_id,
            gradient_checkpointing=gradient_checkpointing,
            tie_word_embeddings=self.tie_word_embeddings,
        )

    def prepare_config_and_inputs_for_common(self):
        (
            config,
            input_ids,
            _,
            sequence_labels,
            token_labels,
            choice_labels,
        ) = self.prepare_config_and_inputs()
        inputs_dict = {"input_ids": input_ids}
        return config, inputs_dict


@unittest.skipIf(
    not is_torch_greater_or_equal_than_2_0, reason="See https://github.com/huggingface/transformers/pull/24204"
)
@require_torch
class Mamba2ModelTest(ModelTesterMixin, GenerationTesterMixin, PipelineTesterMixin, unittest.TestCase):
    all_model_classes = (Mamba2Model, Mamba2ForCausalLM) if is_torch_available() else ()
    all_generative_model_classes = (Mamba2ForCausalLM,) if is_torch_available() else ()
    has_attentions = False  # Mamba does not support attentions
    fx_compatible = False  # FIXME let's try to support this @molbap
    test_torchscript = False  # FIXME I think this should be doable @molbap @ArthurZucker
    test_missing_keys = False
    test_model_parallel = False
    test_pruning = False
    test_head_masking = False  # Mamba does not have attention heads

    pipeline_model_mapping = (
        {"feature-extraction": Mamba2Model, "text-generation": Mamba2ForCausalLM} if is_torch_available() else {}
    )

    def setUp(self):
        self.model_tester = Mamba2ModelTester(self)
        self.config_tester = ConfigTester(
            self, config_class=Mamba2Config, n_embd=37, common_properties=["hidden_size", "num_hidden_layers"]
        )

    def test_initialization(self):
        config, _ = self.model_tester.prepare_config_and_inputs_for_common()

        for model_class in self.all_model_classes:
            model = model_class(config=config)
            for name, param in model.named_parameters():
                if "D" in name:
                    if param.requires_grad:
                        # check if it's a ones like
                        self.assertTrue(torch.allclose(param.data, torch.ones_like(param.data), atol=1e-5, rtol=1e-5))

    @unittest.skip(reason="Mamba 2 weights are not tied")
    def test_tied_weights_keys(self):
        pass

    @unittest.skip(reason="Initialization of mamba2 fails this")
    def test_save_load_fast_init_from_base(self):
        pass

    @unittest.skip(reason="A large mamba2 would be necessary (and costly) for that")
    def test_multi_gpu_data_parallel_forward(self):
        pass

    @unittest.skip(reason="Mamba2 cache doesn't support all arguments tested")
    def test_model_outputs_equivalence(self):
        pass


@require_torch
@slow
class Mamba2IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.model_id = "Molbap/code2"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        # FIXME currently batched generation seems off, as is in the original repo
        self.prompt = ("[INST]Write a hello world program in C++.",)

    @parameterized.expand([
        (torch_device, """<s>[INST] Write a hello world program in C++.[/INST] Sure, here is a simple "Hello, World!" program in C++:\n\n```cpp\n#include <iostream>\n\n"""),
        ("cpu", """<s>[INST] Write a hello world program in C++.[/INST] #include <iostream>\n\nint main() {\n    std::cout << "Hello, World!";\n    return 0;""")
    ])
    def test_simple_generate(self, device, ground_truth_sentence):
        tokenizer = self.tokenizer
        tokenizer.pad_token_id = tokenizer.eos_token_id

        model = Mamba2ForCausalLM.from_pretrained(self.model_id, torch_dtype=torch.float16)
        model.to(device)
        input_ids = tokenizer("[INST]Write a hello world program in C++.[/INST]", return_tensors="pt")["input_ids"].to(
            device
        )

        out = model.generate(input_ids, do_sample=False, use_cache=True, max_new_tokens=30)
        output_sentence = tokenizer.decode(out[0])        
        self.assertEqual(output_sentence, ground_truth_sentence)