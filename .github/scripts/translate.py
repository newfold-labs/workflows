import os
import json
import re
import requests
import polib
from pathlib import Path

TEXT_DOMAIN = os.getenv("TEXT_DOMAIN")

def extract_lang_from_filename(filename):
    pattern = fr'{re.escape(TEXT_DOMAIN)}-([a-z]{{2,3}}(?:_[A-Z]{{2}})?)'
    match = re.search(pattern, filename)
    if match:
        return match.group(1).replace('_', '-')
    return None

def batch_translate(texts, to_lang):
    url = f"https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to={to_lang}"
    headers = {
        "Ocp-Apim-Subscription-Key": os.environ["TRANSLATOR_API_KEY"],
        "Content-Type": "application/json"
    }
    payload = [{"Text": text} for text in texts]
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return [item["translations"][0]["text"] for item in response.json()]

# Translate .po files
for path in Path('.').rglob('*.po'):
    lang = extract_lang_from_filename(path.name)
    print(f"Language detected {lang}")
    if not lang:
        continue

    po = polib.pofile(str(path))
    entries_to_translate = [
        entry for entry in po
        if not entry.msgstr.strip() and entry.msgid.strip()
    ]

    texts = []
    entry_map = []
    for entry in entries_to_translate:
        if entry.msgctxt:
            composed = f"{entry.msgid} ({entry.msgctxt})"
            entry_map.append((entry, True))
        else:
            composed = entry.msgid
            entry_map.append((entry, False))
        texts.append(composed)

    if texts:
        translated_texts = batch_translate(texts, lang)
        for (entry, had_context), translated in zip(entry_map, translated_texts):
            if had_context:
                translated = re.sub(r'\s*\([^()]*\)$', '', translated).strip()
            entry.msgstr = translated.strip()
        po.save()

# Translate .json files
CONTEXT_SEPARATORS = ["|", "\u0004"]

def split_context_key(key):
    for sep in CONTEXT_SEPARATORS:
        if sep in key:
            return key.split(sep, 1)[0], key.split(sep, 1)[1], sep
    return None, key, None

for path in Path('.').rglob('*.json'):
    lang = extract_lang_from_filename(path.name)
    if not lang:
        continue

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
        if context:
            composed = f"{msgid} ({context})"
            key_info_map[key] = (msgid, context, sep)
        else:
            composed = msgid
            key_info_map[key] = (msgid, None, None)

        keys_to_translate.append(composed)

    if keys_to_translate:
        translated_texts = batch_translate(keys_to_translate, lang)
        for key, translated in zip(key_info_map.keys(), translated_texts):
            _, had_context, _ = key_info_map[key]
            if had_context:
                translated = re.sub(r'\s*\(.*\)$', '', translated).strip()
            messages[key] = [translated.strip()]

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
