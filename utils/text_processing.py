import re
from transliterate import translit
from num2words import num2words
from functools import lru_cache
from libs.config import CUSTOM_TRANSLIT

# Предкомпилированные регулярки
RE_CLEAN = re.compile(r'[^\w\s\-.,]')
RE_FLOAT = re.compile(r'^-?\d+(\.\d+)?$')
RE_MIXED = re.compile(r'^[\d\-a-zA-Z]+$')
RE_SPLIT = re.compile(r'\d+|\D+')
RE_LATIN = re.compile(r'[a-zA-Z]')

@lru_cache(maxsize=1000)
def safe_num2words(value):
    try:
        return num2words(round(value, 2), lang='ru')
    except Exception:
        return str(value)

@lru_cache(maxsize=1000)
def safe_translit(word):
    try:
        return translit(word, 'ru')
    except Exception:
        return word

@lru_cache(maxsize=1000)
def prepare_text_for_silero(text):
    processed = []
    text = RE_CLEAN.sub('', text)

    for word in text.split():
        upper = word.upper()

        if upper in CUSTOM_TRANSLIT:
            spoken = CUSTOM_TRANSLIT[upper]

        elif RE_FLOAT.match(word):
            spoken = safe_num2words(float(word))

        elif RE_MIXED.match(word):
            spoken_parts = []
            for part in RE_SPLIT.findall(word):
                if RE_FLOAT.match(part):
                    spoken_parts.append(safe_num2words(float(part)))
                else:
                    spoken_parts.append(safe_translit(part))
            spoken = ' '.join(spoken_parts)

        elif RE_LATIN.search(word):
            spoken = safe_translit(word)

        else:
            spoken = word

        processed.append(spoken)

    return ' '.join(processed)
