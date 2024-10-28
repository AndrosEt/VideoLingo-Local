import re
import os,sys,json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.step2_whisper import get_whisper_language
from core.config_utils import load_key
from typing import Dict, Any, Optional

COMMON_RULES = """
### Critical Requirements
1. DO NOT generate empty lines or lines with only spaces
2. Each line must contain meaningful content
3. Maintain structural consistency with the source text
4. Follow the exact split points marked by [br]
5. Verify all generated content has actual text
"""

## ================================================================
# @ step4_splitbymeaning.py
def get_split_prompt(sentence, num_parts = 2, word_limit = 20):
    # ! only support num_parts = 2

    sentence = preprocess_text(sentence)

    language = get_whisper_language()
    split_prompt = f"""
### Role and Task
You are a professional Netflix subtitle splitter in {language}. Split the given subtitle text into {num_parts} parts, each less than {word_limit} words.

### Key Requirements
1. Maintain sentence coherence and meaning integrity.
2. Split at punctuation marks or conjunctions (e.g., periods, commas, "and", "but", "because").
3. Insert `[br]` ONLY at split positions, NEVER at sentence start/end.
4. Ensure roughly equal part lengths (minimum 3 words per part).
5. No empty spaces before/after splits.

CRITICAL: NEVER insert [br] at sentence start or end. Use [br] only for mid-sentence splits.

### Example
Correct: This is the first part[br]and this is the second part.
Incorrect: [br]This is the whole sentence.[br]

### Process
1. Analyze text structure.
2. Provide 2 split methods with different split points.
3. Evaluate both methods for readability and coherence.
4. Choose the best method (1 or 2).
5. Verify [br] placement is correct.

### Output Format (JSON)
{{
    "analysis": "Brief text structure analysis",
    "split_1": "First split method",
    "split_2": "Second split method",
    "eval": "Concise evaluation of both methods",
    "best": "Best method number (1 or 2)",
    "verification": "Confirm correct [br] placement"
}}

### Self-Check
Ensure:
1. [br] only in sentence middle.
2. Split parts are complete fragments.
3. No [br] at sentence start/end (critical error if violated).

### Given Text
<split_this_sentence>
{sentence}
</split_this_sentence>

""".strip()

    prompt = f"{COMMON_RULES}\n\n{split_prompt}"

    return prompt


## ================================================================
# @ step4_1_summarize.py
def get_summary_prompt(source_content):
    src_language = get_whisper_language()
    TARGET_LANGUAGE = load_key("target_language")
    summary_prompt = f"""
### Role
You are a professional video translation expert and terminology consultant. Your expertise lies not only in accurately understanding the original {src_language} text but also in extracting key professional terms and optimizing the translation to better suit the expression habits and cultural background of {TARGET_LANGUAGE}.

### Task Description 
For the provided original {src_language} video text, you need to:
1. Summarize the video's main topic in one sentence
2. Extract professional terms and names that appear in the video, and provide {TARGET_LANGUAGE} translations or suggest keeping the original language terms. Avoid extracting simple, common words.
3. For each translated term or name, provide a brief explanation

### Analysis and Summary Steps
Please think in two steps, processing the text line by line:  
1. Topic summarization:
   - Quickly skim through the entire text to understand the general idea
   - Summarize the topic in one concise sentence
2. Term and name extraction:
   - Carefully read the entire text, marking professional terms and names
   - For each term or name, provide a {TARGET_LANGUAGE} translation or suggest keeping the original, only the word itself is needed, not the pronunciation
   - Add a brief explanation for each term or name to help the translator understand
   - If the word is a fixed abbreviation or a proper name, please keep the original.

### Output Format
Please output your analysis results in the following JSON format, where <> represents placeholders:
{{
    "theme": "<Briefly summarize the theme of this video in 1 sentence>",
    "terms": [
        {{
            "original": "<Term or name 1 in the {src_language}>",
            "translation": "<{TARGET_LANGUAGE} translation or keep original>",
            "explanation": "<Brief explanation of the term or name>"
        }},
        {{
            "original": "<Term or name 2 in the {src_language}>",
            "translation": "<{TARGET_LANGUAGE} translation or keep original>",
            "explanation": "<Brief explanation of the term or name>"
        }},
        ...
    ]
}}

### Single Output Example (Using French as an example)

{{
    "theme": "Ce vidéo résume le musée du Louvre à Paris.",
    "terms": [
        {{
            "original": "Mona Lisa",
            "translation": "La Joconde",
            "explanation": "Le tableau le plus célèbre du Louvre, un portrait de Léonard de Vinci"
        }},
        {{
            "original": "pyramid",
            "translation": "la pyramide",
            "explanation": "Une grande structure en verre et métal en forme de pyramide située à l'entrée principale du Louvre"
        }},
        {{
            "original": "I.M. Pei",
            "translation": "I.M. Pei",
            "explanation": "L'architecte américain d'origine chinoise qui a conçu la pyramide du Louvre"
        }},
        ...
    ]
}}

### Video text data to be processed
<video_text_to_summarize>
{source_content}
</video_text_to_summarize>
""".strip()

    return summary_prompt

## ================================================================
# @ step5_translate.py & translate_lines.py
def generate_shared_prompt(previous_content_prompt, after_content_prompt, summary_prompt, things_to_note_prompt):
    return f'''### Context Information
<previous_content>
{previous_content_prompt}
</previous_content>

<subsequent_content>
{after_content_prompt}
</subsequent_content>

### Content Summary
{summary_prompt}

### Points to Note
{things_to_note_prompt}'''

def get_prompt_faithfulness(lines, shared_prompt):
    TARGET_LANGUAGE = load_key("target_language")
    # Split lines by \n
    line_splits = lines.split('\n')
    
    # Create JSON return format example
    json_format = {}
    for i, line in enumerate(line_splits, 1):
        json_format[i] = {
            "origin": line,
            "direct": f"<<direct {TARGET_LANGUAGE} translation>>"
        }
    
    src_language = get_whisper_language()
    prompt_faithfulness = f'''
### Role Definition
You are a professional Netflix subtitle translator, fluent in both {src_language} and {TARGET_LANGUAGE}, as well as their respective cultures. Your expertise lies in accurately understanding the semantics and structure of the original {src_language} text and faithfully translating it into {TARGET_LANGUAGE} while preserving the original meaning.

### Task Background
We have a segment of original {src_language} subtitles that need to be directly translated into {TARGET_LANGUAGE}. These subtitles come from a specific context and may contain specific themes and terminology.

### Task Description
Based on the provided original {src_language} subtitles, you need to:
1. Translate the original {src_language} subtitles into {TARGET_LANGUAGE} line by line
2. Ensure the translation is faithful to the original, accurately conveying the original meaning
3. Consider the context and professional terminology

{shared_prompt}

### Translation Principles
1. Faithful to the original: Accurately convey the content and meaning of the original text, without arbitrarily changing, adding, or omitting content.
2. Accurate terminology: Use professional terms correctly and maintain consistency in terminology.
3. Understand the context: Fully comprehend and reflect the background and contextual relationships of the text.

### Subtitle Data
<subtitles>
{lines}
</subtitles>

### Output Format
Please complete the following JSON data, where << >> represents placeholders that should not appear in your answer, and return your translation results in JSON format:
{json.dumps(json_format, ensure_ascii=False, indent=4)}
'''
    
    prompt = f"{COMMON_RULES}\n\n{prompt_faithfulness}"
    return prompt.strip()


def get_prompt_expressiveness(faithfulness_result, lines, shared_prompt):
    TARGET_LANGUAGE = load_key("target_language")
    json_format = {}
    for key, value in faithfulness_result.items():
        json_format[key] = {
            "origin": value['origin'],
            "direct": value['direct'],
            "reflection": "<<reflection on the direct translation version>>",
            "free": f"<<retranslated result, aiming for fluency and naturalness, conforming to {TARGET_LANGUAGE} expression habits, DO NOT leave empty line here!>>"
        }

    src_language = get_whisper_language()
    prompt_expressiveness = f'''
### Role Definition
You are a professional Netflix subtitle translator and language consultant. Your expertise lies not only in accurately understanding the original {src_language} but also in optimizing the {TARGET_LANGUAGE} translation to better suit the target language's expression habits and cultural background.

### Task Background
We already have a direct translation version of the original {src_language} subtitles. Now we need you to reflect on and improve these direct translations to create more natural and fluent {TARGET_LANGUAGE} subtitles.

### Task Description
Based on the provided original {src_language} text and {TARGET_LANGUAGE} direct translation, you need to:
1. Analyze the direct translation results line by line, pointing out existing issues
2. Provide detailed modification suggestions
3. Perform free translation based on your analysis

{shared_prompt}

### Translation Analysis Steps
Please use a two-step thinking process to handle the text line by line:

1. Direct Translation Reflection:
   - Evaluate language fluency
   - Check if the language style is consistent with the original text
   - Check the conciseness of the subtitles, point out where the translation is too wordy, the translation should be close to the original text in length

2. {TARGET_LANGUAGE} Free Translation:
   - Based on the reflection in step 1, perform free translation
   - Aim for contextual smoothness and naturalness, conforming to {TARGET_LANGUAGE} expression habits
   - Ensure it's easy for {TARGET_LANGUAGE} audience to understand and accept
   - Keep the subtitles concise, with a plain and natural language style, and maintain consistency in structure between the free translation and the {src_language} original

### Subtitle Data
<subtitles>
{lines}
</subtitles>

### Output Format
Make sure to generate the correct Json format, don't output " in the value.
Please complete the following JSON data, where << >> represents placeholders that should not appear in your answer, and return your translation results in JSON format:
{json.dumps(json_format, ensure_ascii=False, indent=4)}
'''
    prompt = f"{COMMON_RULES}\n\n{prompt_expressiveness}"
    return prompt.strip()


## ================================================================
# @ step6_splitforsub.py
def get_align_prompt(src_sub, tr_sub, src_part):
    TARGET_LANGUAGE = load_key("target_language")
    src_language = get_whisper_language()
    src_splits = src_part.split('\n')
    num_parts = len(src_splits)
    src_part = src_part.replace('\n', ' [br] ')
    align_prompt = '''
### Role Definition
You are a Netflix subtitle alignment expert fluent in both {src_language} and {target_language}. Your expertise lies in accurately understanding the semantics and structure of both languages, enabling you to flexibly split sentences while preserving the original meaning.

### Task Background
We have {src_language} and {target_language} original subtitles for a Netflix program, as well as a pre-processed split version of {src_language} subtitles. Your task is to create the best splitting scheme for the {target_language} subtitles based on this information.

### Task Description
Based on the provided original {src_language} and {target_language} original subtitles, as well as the pre-processed split version, you need to:
1. Analyze the word order and structural correspondence between {src_language} and {target_language} subtitles
2. Provide 2 different splitting schemes for the {target_language} subtitles
3. Evaluate these schemes and select the best one
4. Never leave empty lines. If it's difficult to split based on meaning, you may appropriately rewrite the sentences that need to be aligned

### Subtitle Data
<subtitles>
{src_language} Original: "{src_sub}"
{target_language} Original: "{tr_sub}"
Pre-processed {src_language} Subtitles ([br] indicates split points): {src_part}
</subtitles>

### Processing Steps
Please follow these steps and provide the results for each step in the JSON output:
1. Analysis and Comparison: Briefly analyze the word order, sentence structure, and semantic correspondence between {src_language} and {target_language} subtitles. Point out key word correspondences, similarities and differences in sentence patterns, and language features that may affect splitting.
2. Start Alignment: Based on your analysis, provide 2 different alignment methods for {target_language} subtitles according to the format. The split positions in {src_language} must be consistent with the pre-processed {src_language} split version and cannot be changed arbitrarily.
3. Evaluation and Selection: Examine and briefly evaluate the 2 schemes, considering factors such as sentence completeness, semantic coherence, and appropriateness of split points.
4. Best Scheme: Select the best alignment scheme, output only a single number, 1 or 2.

### Output Format
Please complete the following JSON data, where << >> represents placeholders, and return your results in JSON format:
{{
    "analysis": "<<Detailed analysis of word order, structure, and semantic correspondence between {src_language} and {target_language} subtitles>>",
    "align_1": [
        {align_parts_json}
    ],
    "align_2": [
        {align_parts_json}
    ],
    "comparison": "<<Brief evaluation and comparison of the 2 alignment schemes>>",
    "best": "<<Number of the best alignment scheme, 1 or 2>>"
}}
'''

    align_parts_json = ','.join(
        f'''
        {{
            "src_part_{i+1}": "<<{src_splits[i]}>>",
            "target_part_{i+1}": "<<Corresponding aligned {TARGET_LANGUAGE} subtitle part>>"
        }}''' for i in range(num_parts)
    )

    prompt = f"{COMMON_RULES}\n\n{align_prompt}"
    return prompt.format(
        src_language=src_language,
        target_language=TARGET_LANGUAGE,
        src_sub=src_sub,
        tr_sub=tr_sub,
        src_part=src_part,
        align_parts_json=align_parts_json,
    )

## ================================================================
# @ step8_gen_audio_task.py @ step10_gen_audio.py
def get_subtitle_trim_prompt(trans_text, duration):
 
    rule = '''Consider a. Reducing filler words without modifying meaningful content. b. Omitting unnecessary modifiers or pronouns, for example:
    - "Please explain your thought process" can be shortened to "Please explain thought process"
    - "We need to carefully analyze this complex problem" can be shortened to "We need to analyze this problem"
    - "Let's discuss the various different perspectives on this topic" can be shortened to "Let's discuss different perspectives on this topic"
    - "Can you describe in detail your experience from yesterday" can be shortened to "Can you describe yesterday's experience" '''

    trim_prompt = '''
### Role
You are a professional subtitle editor, editing and optimizing lengthy subtitles that exceed voiceover time before handing them to voice actors. Your expertise lies in cleverly shortening subtitles slightly while ensuring the original meaning and structure remain unchanged.

### Subtitle Data
<subtitles>
Subtitle: "{trans_text}"
Duration: {duration} seconds
</subtitles>

### Processing Rules
{rule}

### Processing Steps
Please follow these steps and provide the results in the JSON output:
1. Analysis: Briefly analyze the subtitle's structure, key information, and filler words that can be omitted.
2. Trimming: Based on the rules and analysis, optimize the subtitle by making it more concise according to the processing rules.

### Output Format
Please complete the following JSON data, where << >> represents content you need to fill in:
{{
    "analysis": "<<Brief analysis of the subtitle, including structure, key information, and potential processing locations>>",
    "trans_text_processed": "<<Optimized and shortened subtitle in the original subtitle language>>"
}}
'''

    prompt = f"{COMMON_RULES}\n\n{trim_prompt}"
    return prompt.format(
        trans_text=trans_text,
        duration=duration,
        rule=rule
    )

def preprocess_text(text: str) -> str:

    text = re.sub(r'\s+', ' ', text.strip())
    # Ensure there are no consecutive [br] tags
    text = re.sub(r'\[br\]\s*\[br\]', '[br]', text)
    return text


