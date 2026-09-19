"""Application-wide persisted settings and assets."""

from sqlmodel import Field, SQLModel


class AppSetting(SQLModel, table=True):
    __tablename__ = "app_settings"

    key: str = Field(primary_key=True)
    value: str


class AppAsset(SQLModel, table=True):
    __tablename__ = "app_assets"

    key: str = Field(primary_key=True)
    content: bytes
