"""Adlandırılmış SQL şablonu rotalarının istek/yanıt modelleri."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from veri_kalitesi.sql_templates.models import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    ROW_LIMIT_MAX,
    ROW_LIMIT_MIN,
    SQL_MAX_LENGTH,
    TIMEOUT_SECONDS_MAX,
    TIMEOUT_SECONDS_MIN,
    SqlTemplate,
)


class SqlTemplateItemResponse(BaseModel):
    """Tek bir SQL şablonunun taşıma temsili."""

    model_config = ConfigDict(frozen=True)

    template_id: str
    name: str
    description: str | None
    sql_text: str
    default_timeout_seconds: int
    default_row_limit: int
    owner_user_id: str
    created_at: str
    updated_at: str
    version: int

    @classmethod
    def from_domain(cls, template: SqlTemplate) -> "SqlTemplateItemResponse":
        return cls(
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            sql_text=template.sql_text,
            default_timeout_seconds=template.default_timeout_seconds,
            default_row_limit=template.default_row_limit,
            owner_user_id=template.owner_user_id,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat(),
            version=template.version,
        )


class SqlTemplateListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[SqlTemplateItemResponse, ...]


class SqlTemplateDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: SqlTemplateItemResponse


class SqlTemplateCreateRequest(BaseModel):
    """Şablon oluşturma girdisi."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    sql_text: str = Field(min_length=1, max_length=SQL_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    default_timeout_seconds: int = Field(ge=TIMEOUT_SECONDS_MIN, le=TIMEOUT_SECONDS_MAX)
    default_row_limit: int = Field(ge=ROW_LIMIT_MIN, le=ROW_LIMIT_MAX)


class SqlTemplateUpdateRequest(BaseModel):
    """Şablon güncelleme girdisi; verilmeyen alanlar korunur."""

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    sql_text: str | None = Field(default=None, min_length=1, max_length=SQL_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    default_timeout_seconds: int | None = Field(
        default=None, ge=TIMEOUT_SECONDS_MIN, le=TIMEOUT_SECONDS_MAX
    )
    default_row_limit: int | None = Field(default=None, ge=ROW_LIMIT_MIN, le=ROW_LIMIT_MAX)
