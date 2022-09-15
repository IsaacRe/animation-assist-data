from datetime import datetime
from dataclasses import dataclass
from typing import Optional

MAX_TAKEN_DATE = 1660730319
PER_PAGE_DEFAULT = 2


@dataclass
class ImageSearch:
    id: int
    query: str
    last_page_idx: int
    last_image_idx: int
    per_page: int = PER_PAGE_DEFAULT
    max_taken_date: int = MAX_TAKEN_DATE


class InvalidSearchException(Exception):
    pass
