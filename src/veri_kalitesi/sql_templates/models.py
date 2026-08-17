"""Adlandırılmış SQL şablonu domain modeli.

Şablon, çalıştırma ekranında tekrar kullanılan salt okunur bir SQL sorgusunu
ve varsayılan yürütme sınırlarını taşır. Şablonun adı, üretilen CUSTOM_SQL
kuralının ve dolayısıyla çalıştırma kaydının adı olarak kullanılır.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

#: Şablon adının izin verilen uzunluk aralığı.
NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 120
DESCRIPTION_MAX_LENGTH = 500
SQL_MAX_LENGTH = 20_000

#: Varsayılan yürütme sınırlarının kabul edilen aralıkları.
TIMEOUT_SECONDS_MIN = 1
TIMEOUT_SECONDS_MAX = 300
ROW_LIMIT_MIN = 1
ROW_LIMIT_MAX = 100_000

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_ROW_LIMIT = 1_000


@dataclass(frozen=True)
class SqlTemplate:
    """Kaydedilmiş, adlandırılmış salt okunur SQL şablonu."""

    template_id: str
    name: str
    description: str | None
    sql_text: str
    default_timeout_seconds: int
    default_row_limit: int
    owner_user_id: str
    created_at: datetime
    updated_at: datetime
    version: int = 1
