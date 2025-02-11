import gzip
import json
import os
import os.path as osp
import re
import subprocess
import tempfile
from shutil import copyfile
from typing import Dict, Iterable

from datasets import Dataset

from opencompass.openicl.icl_evaluator import BaseEvaluator

from ..base import BaseDataset

_LANGUAGE_NAME_DICT = {
    'cpp': 'CPP',
    'go': 'Go',
    'java': 'Java',
    'js': 'JavaScript',
    'python': 'Python',
    'rust': 'Rust',
}


class HumanevalXDataset(BaseDataset):

    @staticmethod
    def load(path, language, **kwargs):
        assert language in _LANGUAGE_NAME_DICT.keys(), (
            f'language must be in {list(_LANGUAGE_NAME_DICT.keys())}')
        file_path = osp.join(path, f'humanevalx_{language}.jsonl.gz')
        dataset = HumanevalXDataset._stream_jsonl_all(file_path)
        return Dataset.from_list(dataset)

    @staticmethod
    def _stream_jsonl_all(filename: str) -> Iterable[Dict]:
        results = []
        if filename.endswith('.gz'):
            fp = gzip.open(open(filename, 'rb'), 'rt')
        else:
            fp = open(filename, 'r')
        for line in fp:
            if any(not x.isspace() for x in line):
                results.append(json.loads(line))
        fp.close()

        return results


class HumanevalXEvaluator(BaseEvaluator):
    """Evaluator for humanevalx.

    Before you use this Evaluator, launch a code eval service according
    to to readme of https://github.com/Ezra-Yu/code-evaluator.
    Set `ip_address` and `port` according your environment.

    Args:
        language (str): the program language to evaluate.
        ip_address (str): The IP Address of HumanevalX code evaluate service.
            refer to https://github.com/Ezra-Yu/code-evaluator to launch a
            code evaluate service. Defaults to 'localhost'.
        port (int): The port of HumanevalX code evaluate service.
            Defaults to 5000.
        timeout (int): Maximum wait time when accessing the service,
            Defaults to 100.

    TODO: support 'k' of pass@k. default to use k = [1, 10, 100]
    """

    def __init__(self,
                 language,
                 ip_address='localhost',
                 port=5000,
                 timeout=180) -> None:
        assert language in _LANGUAGE_NAME_DICT.keys(), (
            f'language must be in {list(_LANGUAGE_NAME_DICT.keys())}')
        if language == 'rust':
            timeout *= 10  # rust need more time
        self.language = language
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout
        super().__init__()

    def score(self, predictions, references):
        predictions = [{
            'task_id': f'{_LANGUAGE_NAME_DICT[self.language]}/{i}',
            'generation': _clean_up_code(pred, self.language),
        } for i, pred in enumerate(predictions)]
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_out_path = osp.join(tmp_dir,
                                    f'humanevalx_{self.language}.json')
            with open(tmp_out_path, 'w') as f:
                for pred in predictions:
                    f.write(json.dumps(pred) + '\n')

            succeed, output = self._code_eval_service(file_path=tmp_out_path)

            if succeed:
                if isinstance(output, str):
                    return json.loads(output)
                elif isinstance(output, dict):
                    return output

            ref_url = 'https://github.com/Ezra-Yu/code-evaluator'
            result_file_path = os.path.join(
                'outputs', f'humanevalx_{self.language}.json')
            copyfile(tmp_out_path, result_file_path)
            raise Exception(
                f'Call CodeEvalService Error in `HumanevalXEvaluator`, The '
                f"results have been saved in path '{result_file_path}', You "
                'need to check that your code evaluate service is launched and'
                f' the network to service is connected, you can also get '
                f'results directly by using `curl` command refer to {ref_url}.'
                f'\nError Information: {output}')

    def _code_eval_service(self, file_path):
        exec_result = subprocess.run([
            'curl', '-X', 'POST', '-F', f'file=@{file_path}', '-F',
            f'dataset=humanevalx/{self.language}',
            f'{self.ip_address}:{self.port}/evaluate'
        ],
                                     timeout=self.timeout,
                                     capture_output=True)

        if exec_result.returncode == 0 and re.match(
                "\"{.*:.*}\"", exec_result.stdout.decode('utf-8')):
            return True, json.loads(exec_result.stdout.decode('utf-8'))
        else:
            if exec_result.stderr:
                try:
                    err = exec_result.stderr.decode()
                except Exception:
                    err = exec_result.stderr
            else:
                try:
                    err = exec_result.stdout.decode()
                except Exception:
                    err = exec_result.stdout
            return False, err


def _clean_up_code(text: str, language_type: str) -> str:
    """Cleans up the generated code."""
    if language_type.lower() == 'python':
        text_splits = text.split('\n')
        is_empty_line = False
        ind_empty_line = None
        for i, line in enumerate(text_splits):
            if len(line.strip()) > 0 and line[0] != ' ' and line[0] != '\t':
                is_empty_line = True
                ind_empty_line = i
                break
        if is_empty_line:
            text = '\n'.join(text_splits[:ind_empty_line])
        else:
            end_words = [
                '\ndef', '\nclass', '\n#', '\nassert', '\n"""', '\nprint',
                '\nif', '\n\n\n'
            ]
            for w in end_words:
                if w in text:
                    text = text[:text.rfind(w)]
    elif language_type.lower() == 'java':
        main_pos = text.find('public static void main')
        if main_pos != -1:
            text = text[:main_pos] + '}'
        if '}' in text:
            text = text[:text.rfind('}')] + '}'
        if text.count('{') + 1 == text.count('}'):
            text += '\n}'
    elif language_type.lower() == 'go':
        if '\nfunc main(' in text:
            text = text[:text.rfind('func main(')]
        if '}' in text:
            text = text[:text.rfind('}')] + '}'
    elif language_type.lower() == 'cpp':
        if '\nint main()' in text:
            text = text[:text.rfind('int main()')]
        if '}' in text:
            text = text[:text.rfind('}')] + '}'
    elif language_type.lower() == 'js':
        if '}' in text:
            text = text[:text.rfind('}')] + '}'
    elif language_type.lower() == 'rust':
        if '}' in text:
            text = text[:text.rfind('}')] + '}'

    return text
