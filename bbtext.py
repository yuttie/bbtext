from collections import namedtuple
from io import StringIO
import json
import sys
from typing import Union

from pdfminer.layout import LAParams, LTTextBox, LTAnno, LTChar
from pdfminer.high_level import extract_text_to_fp, extract_pages

BB = namedtuple('BB', ['x0', 'y0', 'x1', 'y1'])

query_page_num = int(sys.argv[1])
query = BB(float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]))
pdf_fp = sys.argv[6]

def contained(query: BB, target: LTChar) -> bool:
    return query.x0 <= target.x0 and target.x1 <= query.x1 and \
           query.y0 <= target.y0 and target.y1 <= query.y1

def overlapping(query: BB, target: LTChar) -> bool:
    return not (query.x1 <= target.x0 or \
                target.x1 <= query.x0 or \
                query.y1 <= target.y0 or \
                target.y1 <= query.y0)

def chars_text(chars: list[Union[LTChar, LTAnno]]) -> str:
    return ''.join(c.get_text() for c in chars)

def bb_of(chars: list[Union[LTChar, LTAnno]]) -> BB:
    return BB(
        min(c.x0 for c in chars if isinstance(c, LTChar)),
        min(c.y0 for c in chars if isinstance(c, LTChar)),
        max(c.x1 for c in chars if isinstance(c, LTChar)),
        max(c.y1 for c in chars if isinstance(c, LTChar)),
    )

for i, page in enumerate(extract_pages(sys.argv[6])):
    page_num = i + 1
    if page_num != query_page_num:
        continue
    matched_lines = []
    for elem in page:
        if isinstance(elem, LTTextBox):
            assert (elem.bbox) == (elem.x0, elem.y0, elem.x1, elem.y1)
            text_box = elem
            for line in text_box:
                matched_chars = []
                for char in line:
                    # TextLineElement = Union[LTChar, LTAnno]
                    if isinstance(char, LTChar):
                        assert char.x1 - char.x0 > 0
                        assert char.y1 - char.y0 > 0
                        if contained(query, char):
                            matched_chars.append(char)
                        elif len(matched_chars) > 0:
                            # Nothing left can be a matched char
                            # This is needed to prevent trailing LTAnno to be included
                            break
                    elif isinstance(char, LTAnno):
                        if char.get_text() != '\n':
                            if len(matched_chars) > 0:
                                matched_chars.append(char)
                            else:
                                # Ignore leading LTAnno
                                pass
                if len(matched_chars) > 0:
                    matched_lines.append(matched_chars)
    # Print results
    for line in matched_lines:
        bb = bb_of(line)
        result = dict(
            text=chars_text(line),
            x1=bb.x0,
            y1=bb.y0,
            x2=bb.x1,
            y2=bb.y1,
        )
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.stdout.write('\n')
    # Specified page has been processed
    break
