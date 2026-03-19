"""Port (interfaz abstracta) del repositorio de usuarios."""

from abc import ABC, abstractmethod

from app.domain.models.user import UserProfile
from app.domain.models.user_preference import UserPreference


class UserRepositoryPort(ABC):
    @abstractmethod
    async def get_profile(self, user_id: int) -> UserProfile | None: ...

    @abstractmethod
    async def get_profile_by_chat_id(self, telegram_chat_id: str) -> UserProfile | None: ...

    @abstractmethod
    async def create_profile(self, profile: UserProfile) -> UserProfile: ...

    @abstractmethod
    async def update_profile(self, profile: UserProfile) -> UserProfile: ...

    @abstractmethod
    async def get_preferences(self, user_id: int) -> list[UserPreference]: ...

    @abstractmethod
    async def set_preference(self, pref: UserPreference) -> UserPreference: ...

    @abstractmethod
    async def delete_preference(self, pref_id: int) -> bool: ...
