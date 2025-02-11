"""Self-Consistency Generation Inferencer."""

import os
import os.path as osp
from typing import List, Optional

import mmengine
import torch
from tqdm import tqdm

from opencompass.models.base import BaseModel
from opencompass.registry import ICL_INFERENCERS

from ..icl_prompt_template import PromptTemplate
from ..icl_retriever import BaseRetriever
from ..utils.logging import get_logger
from .icl_base_inferencer import BaseInferencer, CoTInferencerOutputHandler

logger = get_logger(__name__)


@ICL_INFERENCERS.register_module()
class CoTInferencer(BaseInferencer):
    """Self-Consistency Inferencer class to evaluate by multiple generations.

    Attributes:
        model (:obj:`BaseModelWrapper`, optional): The module to inference.
        max_seq_len (:obj:`int`, optional): Maximum number of tokenized words
            allowed by the LM.
        batch_size (:obj:`int`, optional): Batch size for the
            :obj:`DataLoader`.
        output_json_filepath (:obj:`str`, optional): File path for output
            `JSON` file.
        output_json_filename (:obj:`str`, optional): File name for output
            `JSON` file.
        gen_field_replace_token (:obj:`str`, optional): Used to replace the
            generation field token when generating prompts.
        save_every (:obj:`int`, optional): Save intermediate results every
            `save_every` epochs.
        generation_kwargs (:obj:`Dict`, optional): Parameters for the
            :obj:`model.generate()` method.
        sc_size (:obj:`int`, optional): Sample size for Self-Consistency
        infer_type (:obj:`str`, optional): Infer CoT type for
            :obj:`inference()` method.
    """

    def __init__(
            self,
            model: BaseModel,
            max_out_len: int,
            max_seq_len: Optional[int] = None,
            batch_size: Optional[int] = 1,
            gen_field_replace_token: Optional[str] = '',
            output_json_filepath: Optional[str] = './icl_inference_output',
            output_json_filename: Optional[str] = 'predictions',
            save_every: Optional[int] = None,
            fix_id_list: Optional[List[int]] = None,
            sc_size: Optional[int] = 1,
            infer_type: Optional[str] = '',
            cot_prompts: Optional[List[str]] = [''],
            generation_kwargs: dict = {},
            **kwargs) -> None:
        super().__init__(
            model=model,
            max_seq_len=max_seq_len,
            batch_size=batch_size,
            output_json_filename=output_json_filename,
            output_json_filepath=output_json_filepath,
            **kwargs,
        )

        self.gen_field_replace_token = gen_field_replace_token
        self.generation_kwargs = generation_kwargs
        self.max_out_len = max_out_len
        self.fix_id_list = fix_id_list
        self.sc_size = sc_size
        self.cot_prompts = cot_prompts

        if self.model.is_api and save_every is None:
            save_every = 1
        self.save_every = save_every

    def inference(self,
                  retriever: BaseRetriever,
                  ice_template: Optional[PromptTemplate] = None,
                  prompt_template: Optional[PromptTemplate] = None,
                  output_json_filepath: Optional[str] = None,
                  output_json_filename: Optional[str] = None) -> List:
        # 1. Preparation for output logs
        output_handler = CoTInferencerOutputHandler()

        if output_json_filepath is None:
            output_json_filepath = self.output_json_filepath
        if output_json_filename is None:
            output_json_filename = self.output_json_filename

        # 2. Get results of retrieval process
        if 'Fix' in retriever.__class__.__name__:
            ice_idx_list = retriever.retrieve(self.fix_id_list)
        else:
            ice_idx_list = retriever.retrieve()

        # 3. Generate prompts for testing input
        prompt_list, reference_list = self.get_generation_prompt_list_from_retriever_indices(  # noqa
            ice_idx_list,
            retriever,
            self.gen_field_replace_token,
            max_seq_len=self.max_seq_len,
            ice_template=ice_template,
            prompt_template=prompt_template)

        # Create tmp json file for saving intermediate results and future
        # resuming
        index = 0
        tmp_json_filepath = os.path.join(output_json_filepath,
                                         'tmp_' + output_json_filename)
        if osp.exists(tmp_json_filepath):
            # TODO: move resume to output handler
            tmp_result_dict = mmengine.load(tmp_json_filepath)
            output_handler.results_dict = tmp_result_dict
            index = len(tmp_result_dict)

        # 4. Wrap prompts with Dataloader
        dataloader = self.get_dataloader(
            list(zip(prompt_list[index:], reference_list[index:])),
            self.batch_size)

        # 5. Inference for prompts in each batch
        logger.info('Starting inference process...')
        for entry in tqdm(dataloader, disable=not self.is_main_process):
            template_entries = [t[0] for t in entry]
            reference_entries = [t[1] for t in entry]
            # TODO: add more types of CoT method
            # 5-1. Inference sc_size times with local model
            with torch.no_grad():
                parsed_entries = self.model.parse_template(template_entries,
                                                           mode='gen')
                sc_results = []
                sc_thoughts = []
                for _ in range(self.sc_size):
                    results = self.model.generate_from_template(
                        template_entries,
                        max_out_len=self.max_out_len,
                        **self.generation_kwargs)

                    # CoT following steps
                    thoughts = []
                    thoughts.append(results)

                    prev_inputs = [
                        p + r for p, r in zip(parsed_entries, results)
                    ]
                    for cot_prompt in self.cot_prompts:
                        inputs = [prev + cot_prompt for prev in prev_inputs]
                        results = self.model.generate(
                            inputs,
                            max_out_len=self.max_out_len,
                            **self.generation_kwargs)
                        thoughts.append(results)
                        prev_inputs = [p + r for p, r in zip(inputs, results)]

                    thoughts = list(map(list, zip(*thoughts)))
                    sc_thoughts.append(thoughts)
                    sc_results.append(results)
                sc_prediction = list(map(list, zip(*sc_results)))
                sc_thoughts = list(map(list, zip(*sc_thoughts)))
                generated = sc_prediction

            # 5-3. Save current output
            for prompt, prediction, reference, thought in zip(
                    inputs, generated, reference_entries, sc_thoughts):
                output_handler.save_results(prompt, prediction, reference,
                                            thought, index)
                index = index + 1

            # 5-4. Save intermediate results
            if (self.save_every is not None and index % self.save_every == 0
                    and self.is_main_process):
                output_handler.write_to_json(output_json_filepath,
                                             'tmp_' + output_json_filename)

        # 6. Output
        if self.is_main_process:
            os.makedirs(output_json_filepath, exist_ok=True)
            output_handler.write_to_json(output_json_filepath,
                                         output_json_filename)
            if osp.exists(tmp_json_filepath):
                os.remove(tmp_json_filepath)

        return [
            sample['prediction']
            for sample in output_handler.results_dict.values()
        ]

    def get_generation_prompt_list_from_retriever_indices(
            self,
            ice_idx_list: List[List[int]],
            retriever: BaseRetriever,
            gen_field_replace_token: str,
            max_seq_len: Optional[int] = None,
            ice_template: Optional[PromptTemplate] = None,
            prompt_template: Optional[PromptTemplate] = None):
        prompt_list = []
        reference_list = []
        for idx, ice_idx in enumerate(ice_idx_list):
            ice = retriever.generate_ice(ice_idx, ice_template=ice_template)
            reference = retriever.get_label_by_idx(idx)
            reference_list.append(reference)
            prompt = retriever.generate_prompt_for_generate_task(
                idx,
                ice,
                gen_field_replace_token=gen_field_replace_token,
                ice_template=ice_template,
                prompt_template=prompt_template)
            if max_seq_len is not None:
                prompt_token_num = self.model.get_token_len_from_template(
                    prompt, mode='gen')
                while len(ice_idx) > 0 and prompt_token_num > max_seq_len:
                    ice_idx = ice_idx[:-1]
                    ice = retriever.generate_ice(ice_idx,
                                                 ice_template=ice_template)
                    prompt = retriever.generate_prompt_for_generate_task(
                        idx,
                        ice,
                        gen_field_replace_token=gen_field_replace_token,
                        ice_template=ice_template,
                        prompt_template=prompt_template)
                    prompt_token_num = self.model.get_token_len_from_template(
                        prompt, mode='gen')
            prompt_list.append(prompt)
        return prompt_list, reference_list
