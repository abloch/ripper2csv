import sys
from typing import List, Optional, Dict, Set
from glob import glob
from pathlib import Path
from dataclasses import dataclass
import csv

skip_chars = ['[', ']', '◦']
@dataclass
class Word:
    verse_id: str
    form: str
    transliterated_form: str
    fts: List[str]
    parts: Dict[str, str]
    lemma: Optional[str] = None
    transliterated_lemma: Optional[str] = None
    translation: Optional[str] = None
    

ConfigType = Optional[Dict[str, Set[str]]]

DEFAULT_PARTS = {
    'verse': ['Particle', 'Verb', 'Noun', 'Suffix', 'Pronoun', 'Adjective', 'Paragraph', 'Noun'],
    'pos': ['noun', 'verb', 'particle', 'adjective'],
    'number': ['singular', 'plural'],
    'gender': ['masculine', 'feminine'],
    'tense': ['perfect', 'imperfect'],
    'person': ['first', 'second', 'third'],
    'binyan': ['qal', 'piel', 'hifil', 'nifal', 'pual', 'hitpael', 'hofal', 'passiveqal', 'polel', 'hitpolel'],
}

def read_config(source_dir: str) -> ConfigType:
    configfile = source_dir.joinpath('config.txt').absolute()
    if not configfile.exists():
        print("No config file found at " + str(configfile))
        return None
    try:
        ret = {}
        with open(str(configfile), 'r') as file:
            for line in file.readlines():
                parts = line.split(':')
                if len(parts) == 2:
                    terms = parts[1].split(',')
                    title = parts[0].strip()
                    ret[title] = set(terms)
                else:
                    raise ValueError(f"Invalid line in config file: {line}")
        return ret
    except Exception as e:
        print(f"Error reading config file: {e}")
        return None

def write_config(words: List[Word], source_dir: str) -> None:
    parts = set()
    configfile = source_dir.joinpath('config.txt').absolute()
    print("writing config file: " + str(configfile))
    for word in words:
        if word.fts:
            parts.update(word.fts)

    met_parts = sorted(parts, key=lambda x:x.lower())
    with open(str(configfile), "w") as file:
        for fts, features in DEFAULT_PARTS.items():
            file.write(f"{fts}: {', '.join(features)}\n")
            for feature in features:
                if feature in met_parts:
                    met_parts.remove(feature)
            # file.write('\n')
        if met_parts:
            file.write(f"other: {', '.join(met_parts)}")
            
def get_files(source_dir: str) -> List[str]:
    return sorted(glob(str(source_dir) + '/rip_*.txt'))

def has_another_line(file):
    cur_pos = file.tell()
    does_it = bool(file.readline())
    file.seek(cur_pos)
    return does_it

def parse_file(filename: str, config: ConfigType) -> List[Word]:
    ret = []
    with open(filename, "r", encoding="utf-16", errors="ignore") as file:
        while True:
            verse = parse_verse(file, config)
            ret.extend(verse)
            if not has_another_line(file):
                break
    return ret

def parse_verse(open_file: str, config: ConfigType) -> List[Word]:
    verse = open_file.readline().strip()
    assert '\t' not in verse
    ret = []
    while True:
        line = open_file.readline().strip()
        if any(skip_char in line for skip_char in skip_chars):
            continue
        if not line:
            break
        parts = line.split('\t')
        if len(parts) == 3:
            ret.append(parse_suffix(verse, parts, config))
        elif len(parts) in [5, 6]:
            ret.append(parse_word(verse, parts, config))
        else:
            print(ValueError(f"{verse}: Invalid line {line} in {open_file.name} (it has {len(parts)} parts)"))
    return ret

def parse_word(verse: str, parts: List[str], config: ConfigType) -> Word:
    return Word(
        verse_id=verse,
        form=parts[0],
        transliterated_form=parts[1],
        lemma=parts[2],
        transliterated_lemma=parts[3],
        fts=parts[4].split(' ') if len(parts) == 6 else None,
        parts=handle_parts(parts[4], config)  if len(parts) == 6 else None,
        translation=parts[-1],
    )

def parse_suffix(verse: str, parts: List[str], config: ConfigType) -> Word:
    return Word(
        verse_id=verse,
        form=parts[0],
        transliterated_form=parts[1],
        fts=parts[2].split(' '),
        parts=handle_parts(parts[2], config),
    )

def handle_parts(parts: str, config: ConfigType) -> Dict[str, str]:
    if config is None:
        return
    return {part: config.get(part, part) for part in parts.split(' ')}

def write_csv(words: List[Word], source_dir: str, config: ConfigType) -> None:
    out = []
    
    for word in words:
        w = {
            'verse_id': word.verse_id,
            'form': word.form,
            'transliterated_form': word.transliterated_form,
            'lemma': word.lemma,
            'transliterated_lemma': word.transliterated_lemma,
            'fts': "[" + ', '.join(word.fts) + "]" if word.fts else None,
            'translation': word.translation,
        }
        for config_title, config_terms in config.items():
            met_terms = config_terms.intersection(set(word.parts)) if word.parts else None
            w[config_title] = ','.join(met_terms) if met_terms else ""
        out.append(w)
    outfile = source_dir.joinpath('output.csv').absolute()
    print("writing output file: " + str(outfile))
    with open(str(outfile), 'w') as file:
        csv.DictWriter(file, fieldnames=w.keys()).writeheader()
        for row in out:
            csv.DictWriter(file, fieldnames=w.keys()).writerow(row)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        source_dir = Path(sys.argv[1]).absolute()
    else:
        source_dir = Path(__file__.replace('main.py', 'source'))
    config = read_config(source_dir)
    words = []
    for file in get_files(source_dir):
        words.extend(parse_file(file, config))
    if config is None:
        write_config(words, source_dir)
    else:
        write_csv(words, source_dir, config)