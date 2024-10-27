import os, sys, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from threading import Lock
import json_repair
import json 
import ollama
import time
from core.config_utils import load_key

LOG_FOLDER = 'output/gpt_log'
LOCK = Lock()

def save_log(model, prompt, response, log_title = 'default', message = None):
    os.makedirs(LOG_FOLDER, exist_ok=True)
    log_data = {
        "model": model,
        "prompt": prompt,
        "response": response,
        "message": message
    }
    log_file = os.path.join(LOG_FOLDER, f"{log_title}.json")
    
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    else:
        logs = []
    logs.append(log_data)
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=4)
        
def check_ask_gpt_history(prompt, model, log_title):
    # check if the prompt has been asked before
    if not os.path.exists(LOG_FOLDER):
        return False
    file_path = os.path.join(LOG_FOLDER, f"{log_title}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                if item["prompt"] == prompt and item["model"] == model:
                    return item["response"]
    return False

def ask_gpt(prompt, response_json=True, valid_def=None, log_title='default'):
    api_set = load_key("api")
    llm_support_json = load_key("llm_support_json")
    
    with LOCK:
        history_response = check_ask_gpt_history(prompt, api_set["model"], log_title)
        if history_response:
            return history_response
    
    max_retries = 10
    for attempt in range(max_retries):
        try:
            response = ollama.chat(
                model=api_set["model"],
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                format='json' if response_json else None,
                stream=False
            )
            
            if response_json:
                try:
                    content = response['message']['content']
                    
                    json_content = json_repair.loads(content)
                    
                    if valid_def:
                        valid_response = valid_def(json_content)
                        if valid_response['status'] != 'success':
                            save_log(api_set["model"], prompt, json_content, log_title="error", message=valid_response['message'])
                            raise ValueError(f"❎ API response error: {valid_response['message']}")
                    
                    response_data = json_content
                    break
                except Exception as e:
                    print(f"❎ json_repair parsing failed. Retrying: '''{content}'''")
                    save_log(api_set["model"], prompt, content, log_title="error", message=f"json_repair parsing failed.")
                    if attempt == max_retries - 1:
                        raise Exception(f"JSON parsing still failed after {max_retries} attempts: {e}")
            else:
                response_data = response['message']['content']
                break
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Error occurred: {e}\nRetrying...")
                time.sleep(2)
            else:
                raise Exception(f"Still failed after {max_retries} attempts: {e}")

    with LOCK:
        if log_title != 'None':
            save_log(api_set["model"], prompt, response_data, log_title=log_title)

    return response_data


if __name__ == '__main__':
    print(ask_gpt('hi there hey response in json format, just return 200.' , response_json=True, log_title=None))
