"""Run locally to save a Gemini key without printing it or putting it in chat."""
from pathlib import Path
from getpass import getpass
from dotenv import set_key

if __name__ == '__main__':
    key = getpass('Paste your Gemini API key (hidden): ').strip()
    if not key:
        raise SystemExit('No key entered. Configuration unchanged.')
    path = Path(__file__).parent / '.env'
    path.touch(exist_ok=True)
    set_key(str(path), 'LLM_API_KEY', key)
    set_key(str(path), 'LLM_PROVIDER', 'gemini')
    set_key(str(path), 'LLM_MODEL', 'gemini-3.8-flash')
    print('Gemini configuration saved locally. Restart the analytics backend.')
