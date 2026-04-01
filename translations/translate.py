"""
Translate empty msgstr entries in PO files under languages/ via Azure Translator.

Locale JSON (and other derived assets) are not handled here; they are regenerated
from the PO catalogs by the repo's i18n-ci-post / WP-CLI flow.
"""
import os
import re
import requests
import polib
from pathlib import Path

TEXT_DOMAIN = os.getenv("TEXT_DOMAIN")
# When saving PO files, polib only supports one formatting option: wrapwidth.
# - TRANSLATE_PO_WRAPWIDTH: max line length (default 77). Used only when TRANSLATE_PO_NOWRAP is not set.
# - TRANSLATE_PO_NOWRAP: if set (e.g. "1" or "true"), use wrapwidth=0 so long msgid/msgstr are not
#   broken across lines.
#   Note: polib always joins reference comments (#: file:line) with spaces;
#   with nowrap they become one long line; with wrapping it puts multiple refs per line up to wrapwidth.
#   Polib does not support "one #: per line".
PO_NOWRAP = os.getenv("TRANSLATE_PO_NOWRAP", "").lower() in ("1", "true", "yes")
PO_WRAPWIDTH = 0 if PO_NOWRAP else int(os.getenv("TRANSLATE_PO_WRAPWIDTH", "77"))

def extract_lang_from_filename(filename):
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

# Translate .po files only (only save when we actually translate something to avoid formatting-only diffs).
for path in Path('languages').rglob('*.po'):
    lang = extract_lang_from_filename(path.name)
    print(f"Language detected: {lang}")
    if not lang:
        continue

    print(f"Processing file: {path}")
    po = polib.pofile(str(path), wrapwidth=PO_WRAPWIDTH)
    entries_to_translate = [entry for entry in po if not entry.msgstr.strip() and entry.msgid.strip()]

    if not entries_to_translate:
        continue

    def get_po_id_context(entry):
        return entry.msgid, entry.msgctxt

    def apply_po_translation(entry, translated):
        entry.msgstr = translated

    translate_entries(entries_to_translate, get_po_id_context, apply_po_translation, lang)
    po.save()
