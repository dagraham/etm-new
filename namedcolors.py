#!/usr/bin/env python3
"""
Demonstration of all the ANSI colors.
"""
from prompt_toolkit import print_formatted_text as pft
from prompt_toolkit import HTML
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles.named_colors import NAMED_COLORS
import re


import re

import re

def sort_by_final_suffix(color_names):
    def split_final_camel_case(name):
        # Split the name into all components based on CamelCase
        parts = re.findall(r'[A-Z][a-z]+', name)
        if len(parts) > 1:
            # Use the last part as the suffix, and the rest as the prefix
            prefix = ''.join(parts[:-1])
            suffix = parts[-1]
            return suffix.lower(), prefix.lower()
        else:
            # If only one part, treat the whole name as both prefix and suffix
            return name.lower(), ''

    # Sort by the final suffix, then by the prefix
    return sorted(color_names, key=split_final_camel_case)



def main():
    sorted_color_names = sort_by_final_suffix(NAMED_COLORS.keys())
    tokens = FormattedText(
        [('fg:' + name, name + '  ') for name in sorted_color_names]
    )

    pft(HTML('\n<u>Sorted Named colors, hex codes.</u>'))
    print(", ".join([f"{k}: {v}" for k, v in NAMED_COLORS.items()]))

    pft(HTML('\n<u>Sorted Named colors, using 16 color output.</u>'))
    pft('(Note that it doesn\'t really make sense to use named colors ')
    pft('with only 16 color output.)')
    pft(tokens, color_depth=ColorDepth.DEPTH_4_BIT)

    pft(HTML('\n<u>Sorted Named colors, use 256 colors.</u>'))
    pft(tokens)

    pft(HTML('\n<u>Sorted Named colors, using True color output.</u>'))
    pft(tokens, color_depth=ColorDepth.TRUE_COLOR)


if __name__ == '__main__':
    main()

