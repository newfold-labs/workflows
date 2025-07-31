import os
import json
import re
import requests
import polib
from pathlib import Path

def extract_lang_from_filename(filename):
    TEXT_DOMAIN = os.getenv("TEXT_DOMAIN")

    pattern = fr'{re.escape(TEXT_DOMAIN)}-([a-z]{{2,3}}(?:_[A-Z]{{2}})?)'
    match = re.search(pattern, filename)
    if match:
        return match.group(1).replace('_', '-')
    return None

def batch_translate(texts, to_lang):
    url = f"https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=en&to={to_lang}"
    headers = {
        "Ocp-Apim-Subscription-Key": os.environ["TRANSLATOR_API_KEY"],
        "Content-Type": "application/json"
    }
    payload = [{"Text": text} for text in texts]
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return [item["translations"][0]["text"] for item in response.json()]
    except requests.exceptions.RequestException as e:
        print(f"API request failed for lang {to_lang}:", str(e))
        return None

def compose_msg_with_context(msgid, context):
    return f"{msgid} ({context})" if context else msgid

def strip_context_from_translation(text):
    return re.sub(r'\([^()]*\)\s*$', '', text).strip()

def translate_entries(entries, get_id_context, apply_translation, lang):
    texts = []
    metadata = []

    for entry in entries:
        msgid, context = get_id_context(entry)
        if msgid.strip():
            texts.append(compose_msg_with_context(msgid, context))
            metadata.append((entry, bool(context)))

    if not texts:
        return

    translated_texts = batch_translate(texts, lang)
    if not translated_texts:
        return

    for (entry, had_context), translated in zip(metadata, translated_texts):
        translated = strip_context_from_translation(translated) if had_context else translated.strip()
        apply_translation(entry, translated)

# Translate .po files
for path in Path('languages').rglob('*.po'):
    lang = extract_lang_from_filename(path.name)
    print(f"Language detected: {lang}")
    if not lang:
        continue

    print(f"Processing file: {path}")
    po = polib.pofile(str(path))
    entries_to_translate = [entry for entry in po if not entry.msgstr.strip() and entry.msgid.strip()]

    def get_po_id_context(entry):
        return entry.msgid, entry.msgctxt

    def apply_po_translation(entry, translated):
        entry.msgstr = translated

    translate_entries(entries_to_translate, get_po_id_context, apply_po_translation, lang)
    po.save()

# Translate .json files
CONTEXT_SEPARATORS = ["|", "\u0004"]

def split_context_key(key):
    for sep in CONTEXT_SEPARATORS:
        if sep in key:
            context, msgid = key.split(sep, 1)
            return context, msgid, sep
    return None, key, None

for path in Path('languages').rglob('*.json'):
    lang = extract_lang_from_filename(path.name)
    print(f"Language detected: {lang}")
    if not lang:
        continue

    print(f"Processing file: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        try:
            content = json.load(f)
        except json.JSONDecodeError:
            continue

    if "locale_data" not in content or "messages" not in content["locale_data"]:
        continue

    messages = content["locale_data"]["messages"]
    keys_to_translate = []
    key_info_map = {}

    for key, val in messages.items():
        if key == "" or not isinstance(val, list) or val[0].strip():
            continue
        context, msgid, sep = split_context_key(key)
        composed = compose_msg_with_context(msgid, context)
        keys_to_translate.append(composed)
        key_info_map[key] = (msgid, context, sep)

    if not keys_to_translate:
        continue

    translated_texts = batch_translate(keys_to_translate, lang)
    if not translated_texts:
        continue

    for key, translated in zip(key_info_map.keys(), translated_texts):
        _, context, _ = key_info_map[key]
        if context:
            translated = strip_context_from_translation(translated)
        messages[key] = [translated.strip()]

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
