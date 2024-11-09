import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ask_gpt import ask_gpt
from core.prompts_storage import generate_shared_prompt, get_prompt_faithfulness, get_prompt_expressiveness
from rich.panel import Panel
from rich.console import Console
from rich.table import Table
from rich import box
import re

console = Console()

def valid_translate_result(result: dict, required_keys: list, required_sub_keys: list):
    # Check for the required key
    if not all(key in result for key in required_keys):
        return {"status": "error", "message": f"Missing required key(s): {', '.join(set(required_keys) - set(result.keys()))}"}
    
    # Check for required sub-keys in all items
    for key in result:
        if not all(sub_key in result[key] for sub_key in required_sub_keys):
            return {"status": "error", "message": f"Missing required sub-key(s) in item {key}: {', '.join(set(required_sub_keys) - set(result[key].keys()))}"}
    
    # Check if all sub-keys values are not empty
    def remove_punctuation(text):
        return re.sub(r'[^\w\s]', '', text).strip()
    for key in result:
        for sub_key in required_sub_keys:
            translate_result = remove_punctuation(result[key][sub_key]).strip()
            if not translate_result:
                return {"status": "error", "message": f"Empty value for sub-key '{sub_key}' in item {key}"}
    
    return {"status": "success", "message": "Translation completed"}

def translate_lines(lines, previous_content_prompt, after_cotent_prompt, things_to_note_prompt, summary_prompt, index = 0):
    shared_prompt = generate_shared_prompt(previous_content_prompt, after_cotent_prompt, summary_prompt, things_to_note_prompt)

    # Retry translation if the length of the original text and the translated text are not the same, or if the specified key is missing
    def retry_translation(prompt, step_name):
        def valid_faith(response_data):
            return valid_translate_result(response_data, ['1'], ['direct'])
        def valid_express(response_data):
            return valid_translate_result(response_data, ['1'], ['free'])
        for retry in range(10):
            if step_name == 'faithfulness':
                result = ask_gpt(prompt, response_json=True, valid_def=valid_faith, log_title=f'translate_{step_name}')
            elif step_name == 'expressiveness':
                result = ask_gpt(prompt, response_json=True, valid_def=valid_express, log_title=f'translate_{step_name}')
            if len(lines.split('\n')) == len(result):
                return result
            if retry != 2:
                console.print(f'[yellow]⚠️ {step_name.capitalize()} translation of block {index} failed, Retry...[/yellow]')
        raise ValueError(f'[red]❌ {step_name.capitalize()} translation of block {index} failed after 10 retries. Please check your input text.[/red]')

    ## Step 1: Faithful to the Original Text
    prompt1 = get_prompt_faithfulness(lines, shared_prompt)
    faith_result = retry_translation(prompt1, 'faithfulness')

    for i in faith_result:
        faith_result[i]["direct"] = faith_result[i]["direct"].replace('\n', ' ')

    ## Step 2: Express Smoothly  
    prompt2 = get_prompt_expressiveness(faith_result, lines, shared_prompt)
    express_result = retry_translation(prompt2, 'expressiveness')

    table = Table(title="Translation Results", show_header=False, box=box.ROUNDED)
    table.add_column("Translations", style="bold")
    for i, key in enumerate(express_result):
        table.add_row(f"[cyan]Origin:  {faith_result[key]['origin']}[/cyan]")
        table.add_row(f"[magenta]Direct:  {faith_result[key]['direct']}[/magenta]")
        table.add_row(f"[green]Free:    {express_result[key]['free']}[/green]")
        if i < len(express_result) - 1:
            table.add_row("[yellow]" + "-" * 50 + "[/yellow]")

    console.print(table)

    translate_result = "\n".join([express_result[i]["free"].replace('\n', ' ').strip() for i in express_result])
    
    # 改进的错误信息
    if len(lines.split('\n')) != len(translate_result.split('\n')):
        orig_lines = lines.split('\n')
        trans_lines = translate_result.split('\n')
        console.print(Panel(
            f'[red]❌ Translation of block {index} failed:\n'
            f'Original lines: {len(orig_lines)}\n'
            f'Translated lines: {len(trans_lines)}\n'
            f'Please check `output/gpt_log/translate_expressiveness.json`\n'
            f'You may need to adjust the translation prompt or retry.[/red]'
        ))
        raise ValueError(
            f'Translation length mismatch:\n'
            f'Original ({len(orig_lines)} lines):\n{lines}\n'
            f'Translation ({len(trans_lines)} lines):\n{translate_result}'
        )

    return translate_result, lines


if __name__ == '__main__':
    # test e.g.
    lines = '''All of you know Andrew Ng as a famous computer science professor at Stanford.
He was really early on in the development of neural networks with GPUs.
Of course, a creator of Coursera and popular courses like deeplearning.ai.
Also the founder and creator and early lead of Google Brain.'''
    previous_content_prompt = None
    after_cotent_prompt = None
    things_to_note_prompt = None
    summary_prompt = None
    translate_lines(lines, previous_content_prompt, after_cotent_prompt, things_to_note_prompt, summary_prompt)
