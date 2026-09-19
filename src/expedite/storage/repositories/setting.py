"""Application setting and asset repositories."""

from sqlmodel import Session

from expedite.models import AppAsset, AppSetting
from expedite.storage.repositories.base import Repository


class AppSettingRepository(Repository[AppSetting]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AppSetting)


class AppAssetRepository(Repository[AppAsset]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AppAsset)
