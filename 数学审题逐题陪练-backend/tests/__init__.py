# -*- coding: utf-8 -*-
"""测试。跑法：在 backend 根目录下 `python -m unittest discover -s tests -v`"""

import sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
if str(根) not in sys.path:
    sys.path.insert(0, str(根))
