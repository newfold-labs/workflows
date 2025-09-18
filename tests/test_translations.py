import pytest
import json
import os
import sys
import tempfile
import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
import requests
import polib

# Set the text domain.
os.environ["TEXT_DOMAIN"] = "newfold-labs-workflows"
os.environ["TRANSLATOR_API_KEY"] = "api-key-1234-secure"

# Import the translation script from translations/translate.py
script_path = Path(__file__).parent.parent / "translations" / "translate.py"

if not script_path.exists():
    raise FileNotFoundError(f"Could not find translate.py at: {script_path.absolute()}")

# Dynamically import the translation script
spec = importlib.util.spec_from_file_location("translate", script_path)
translate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(translate_module)

# Import the functions from the loaded module
extract_lang_from_filename = translate_module.extract_lang_from_filename
batch_translate = translate_module.batch_translate
compose_msg_with_context = translate_module.compose_msg_with_context
strip_context_from_translation = translate_module.strip_context_from_translation
translate_entries = translate_module.translate_entries
split_context_key = translate_module.split_context_key
CONTEXT_SEPARATORS = translate_module.CONTEXT_SEPARATORS

class TestExtractLangFromFilename:

    """Test language extraction from filenames."""

    TEXT_DOMAIN = os.environ["TEXT_DOMAIN"]

    @pytest.mark.parametrize("filename,expected", [
        # PO files with two character locale codes.
        (f"{TEXT_DOMAIN}-pt.po", "pt"),
        (f"{TEXT_DOMAIN}-de.po", "de"),
        (f"{TEXT_DOMAIN}-es.po", "es"),
        (f"{TEXT_DOMAIN}-fr.po", "fr"),
        # JSON files with two character locale codes.
        (f"{TEXT_DOMAIN}-pt.json", "pt"),
        (f"{TEXT_DOMAIN}-de.json", "de"),
        (f"{TEXT_DOMAIN}-es.json", "es"),
        (f"{TEXT_DOMAIN}-fr.json", "fr"),
        # Four character locale codes.
        (f"{TEXT_DOMAIN}-fr_FR.po", "fr-FR"),
        (f"{TEXT_DOMAIN}-de_DE.po", "de-DE"),
        (f"{TEXT_DOMAIN}-es_ES.po", "es-ES"),
        # Four character locale codes with regional variant.
        (f"{TEXT_DOMAIN}-pt_BR.po", "pt-BR"),
        (f"{TEXT_DOMAIN}-de_CH.po", "de-CH"),
        # Filenames with unexpected syntax should not match.
        (f"{TEXT_DOMAIN}.es_AR.po", None),
        (f"{TEXT_DOMAIN}_en_AU.po", None),
        # Files without text domain should not match.
        ("unrelated.txt", None),
        ("some-other-text-domain.po", None),
        ("some-other-text-domain-pt.po", None),
        ("some-other-text-domain-pt_BR.po", None),
        ("some-other-text-domain.po", None),
        ("unrelated.txt", None),
        ("", None)
    ])

    def test_extract_lang_from_filename(self, filename, expected):
        assert extract_lang_from_filename(filename) == expected

class TestComposeMsgWithContext:
    """Test message composition with context."""

    @pytest.mark.parametrize(
        "message, context, expected",
        [
            ("Hello", "greeting", "Hello (greeting)"),
            ("Hello", None, "Hello"),
            ("Hello", "", "Hello"),
            ("", "context", " (context)"),
            ("Hello & goodbye", "special chars", "Hello & goodbye (special chars)"),
        ]
    )
    def test_compose_msg_with_context(self, message, context, expected):
        """Test composing message with various contexts and msgids."""
        result = compose_msg_with_context(message, context)
        assert result == expected


class TestStripContextFromTranslation:
    """Test context stripping from translations."""

    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("Hola (saludo)", "Hola"),
            ("Bonjour (greeting)", "Bonjour"),
            ("Hola", "Hola"),
            ("Simple text", "Simple text"),
            ("Text (first) (last)", "Text (first)"),
            ("Text (nested (inner))", "Text (nested (inner))"),
            ("  Hola (context)  ", "Hola"),
            ("Text   (context)", "Text"),
            ("", ""),
            ("(context)", ""),
        ]
    )
    def test_strip_context(self, input_text, expected):
        assert strip_context_from_translation(input_text) == expected

class TestSplitContextKey:
    """Test context key splitting for JSON files."""

    @pytest.mark.parametrize(
        "key,expected_context,expected_msgid,expected_sep",
        [
            ("greeting|Hello", "greeting", "Hello", "|"),
            ("greeting\u0004Hello", "greeting", "Hello", "\u0004"),
            ("Hello", None, "Hello", None),
            ("greeting|Hello|World", "greeting", "Hello|World", "|"),
            ("|Hello", "", "Hello", "|"),
            ("greeting|", "greeting", "", "|"),
            ("greeting|Hello\u0004World", "greeting", "Hello\u0004World", "|"),
        ]
    )
    def test_split_context_key(self, key, expected_context, expected_msgid, expected_sep):
        context, msgid, sep = split_context_key(key)
        assert context == expected_context
        assert msgid == expected_msgid
        assert sep == expected_sep


class TestBatchTranslate:
    """Test batch translation functionality."""

    TRANSLATOR_API_KEY = os.environ["TRANSLATOR_API_KEY"]

    @pytest.fixture(autouse=True)
    def setup_api_key(self):
        """Set up API key environment variable."""
        with patch.dict(os.environ, {'TRANSLATOR_API_KEY': 'test-key'}):
            yield

    @patch('requests.post')
    def test_batch_translate_success(self, mock_post):
        """Test successful batch translation."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {"translations": [{"text": "Hola"}]},
            {"translations": [{"text": "Adiós"}]}
        ]
        mock_post.return_value = mock_response

        texts = ["Hello", "Goodbye"]
        result = batch_translate(texts, "es")

        assert result == ["Hola", "Adiós"]

        # Confirm only one request.
        mock_post.assert_called_once()

        # Extract call args
        call_args = mock_post.call_args
        called_url = call_args[0][0]
        called_headers = call_args[1]['headers']
        called_json = call_args[1]['json']

        # Check URL query parameters
        assert "api-version=3.0" in called_url
        assert "from=en" in called_url
        assert "to=es" in called_url

        # Check headers
        assert called_headers['Ocp-Apim-Subscription-Key'] == "test-key"

        # Check body
        assert called_json == [{"Text": "Hello"}, {"Text": "Goodbye"}]

    @patch('requests.post')
    def test_batch_translate_api_error(self, mock_post, capsys):
        """Test API request failure."""
        mock_post.side_effect = requests.exceptions.RequestException("API Error")

        texts = ["Hello", "Goodbye"]
        result = batch_translate(texts, "es")

        assert result is None

        # Confirm error message was output.
        captured = capsys.readouterr()
        assert "API request failed for lang es: API Error" in captured.out or "API Error" in captured.err

    @patch('requests.post')
    def test_batch_translate_http_error(self, mock_post):
        """Test HTTP error response."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_post.return_value = mock_response

        texts = ["Hello"]
        result = batch_translate(texts, "es")

        assert result is None

    @patch('requests.post')
    def test_batch_translate_empty_texts(self, mock_post):
        """Test with empty text list."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = []
        mock_post.return_value = mock_response

        result = batch_translate([], "es")

        assert result == []

    @patch('requests.post')
    def test_batch_translate_missing_api_key(self, mock_post, capsys):
        """Test with missing API key, expect 401 Unauthorized error."""
        mock_post.side_effect = requests.exceptions.RequestException("401 Client Error: Unauthorized")

        texts = ["Hello", "Goodbye"]
        result = batch_translate(texts, "es")

        assert result is None

        # Confirm error message was output.
        captured = capsys.readouterr()
        assert "API request failed for lang es: 401 Client Error: Unauthorized" in captured.out

    def test_translate_entries_with_real_helpers(self):
        """Test translate_entries function with mocked batch_translate."""

        class SampleEntry:
            def __init__(self, msgid, tcomment=None, msgstr="", msgctxt=None):
                self.msgid = msgid
                self.msgstr = msgstr
                self.tcomment = tcomment
                self.msgctxt = msgctxt

        entries = [
            SampleEntry("Hello", tcomment="admin", msgctxt="admin"),
            SampleEntry("Goodbye", tcomment=None, msgctxt=None),
            SampleEntry("", tcomment="empty-msgid", msgctxt="empty-msgid"),
            SampleEntry("Special ©✓", tcomment="unicode", msgctxt="unicode"),
            SampleEntry("Duplicate", tcomment="dup", msgctxt="dup"),
            SampleEntry("Duplicate", tcomment="dup", msgctxt="dup"),
            SampleEntry("Context|Separator", tcomment="with|sep", msgctxt="with|sep"),
            SampleEntry("None tcomment", tcomment=None, msgctxt=None),
        ]

        mock_translations = [
            "Hola (admin)",
            "Adiós",
            "Especial ©✓ (unicode)",
            "Duplicado (dup)",
            "Duplicado (dup)",
            "Contexto|Separador (with|sep)",
            "Ninguno",
        ]

        # Define helper functions that match the actual script.
        def get_po_id_context(entry):
            return entry.msgid, entry.msgctxt

        def apply_po_translation(entry, translated):
            entry.msgstr = translated

        # Use patch.object to mock batch_translate.
        with patch.object(translate_module, 'batch_translate', return_value=mock_translations):
            translate_entries(entries, get_po_id_context, apply_po_translation, "es")

        # Check all results at once.
        expected_results = [
            "Hola",
            "Adiós",
            "",
            "Especial ©✓",
            "Duplicado",
            "Duplicado",
            "Contexto|Separador",
            "Ninguno",
        ]

        actual_results = [entry.msgstr for entry in entries]
        assert actual_results == expected_results

if __name__ == "__main__":
    pytest.main([__file__])
