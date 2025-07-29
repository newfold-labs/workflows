import os
import json
import re
import requests
import polib
import time

from pathlib import Path

TEXT_DOMAIN = os.getenv("TEXT_DOMAIN")
RETRY_ATTEMPTS = os.getenv("RETRY_ATTEMPTS")

session = requests.Session()

def extract_lang_from_filename(filename):
    pattern = fr'{re.escape(TEXT_DOMAIN)}-([a-z]{{2,3}}(?:_[A-Z]{{2}})?)'
    match = re.search(pattern, filename)
    if match:
        return match.group(1).replace('_', '-')
    return None

def batch_translate(texts, to_lang, session):
    url = f"https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=en&to={to_lang}"
    headers = {
        "Ocp-Apim-Subscription-Key": os.environ["TRANSLATOR_API_KEY"],
        "Content-Type": "application/json"
    }
    payload = [{"Text": text} for text in texts]

    max_retries = RETRY_ATTEMPTS
    for attempt in range(1, max_retries + 1):
        try:
            response = session.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return [item["translations"][0]["text"] for item in response.json()]
        except requests.exceptions.HTTPError:
            status_code = response.status_code

            try:
                error_data = response.json().get("error", {})
                error_message = error_data.get("message", "")
                error_code = error_data.get("code", "")
            except (ValueError, KeyError, json.JSONDecodeError):
                error_message = "Unable to parse error message"
                error_code = status_code

            if status_code == 429:
                wait_time = 2 ** attempt

                print(f"[{to_lang}] Rate limit hit (attempt {attempt}/{max_retries}): {error_message}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                print(f"[{to_lang}] API error: {error_code} — {error_message}")
                break

    return None

def compose_msg_with_context(msgid, context):
    return f"{msgid} ({context})" if context else msgid

def strip_context_from_translation(text):
    return re.sub(r'\s*\([^()]*\)$', '', text).strip()

def translate_entries(entries, get_id_context, apply_translation, lang, session):
    texts = []
    metadata = []

    for entry in entries:
        msgid, context = get_id_context(entry)
        if msgid.strip():
            texts.append(compose_msg_with_context(msgid, context))
            metadata.append((entry, bool(context)))

    if not texts:
        return

    translated_texts = batch_translate(texts, lang, session)
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

    translate_entries(entries_to_translate, get_po_id_context, apply_po_translation, lang, session)
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

    translated_texts = batch_translate(keys_to_translate, lang, session)
    if not translated_texts:
        continue

    for key, translated in zip(key_info_map.keys(), translated_texts):
        _, context, _ = key_info_map[key]
        if context:
            translated = strip_context_from_translation(translated)
        messages[key] = [translated.strip()]

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
