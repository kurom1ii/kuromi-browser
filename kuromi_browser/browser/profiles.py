"""
Browser Profile System for kuromi-browser.

Manages persistent browser profiles with user data directories,
extensions, and settings. Enables multi-user and multi-session support.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from kuromi_browser.models import Fingerprint, ProxyConfig

logger = logging.getLogger(__name__)


# Default profiles directory
DEFAULT_PROFILES_DIR = Path.home() / ".kuromi-browser" / "profiles"


class ProfileState(str, Enum):
    """Profile lifecycle states."""

    IDLE = "idle"
    """Profile is not in use."""

    ACTIVE = "active"
    """Profile is currently being used by a browser."""

    LOCKED = "locked"
    """Profile is locked by another process."""


@dataclass
class ProfileMetadata:
    """Metadata about a browser profile."""

    id: str
    """Unique profile identifier."""

    name: str
    """Human-readable profile name."""

    created_at: str
    """ISO timestamp of creation."""

    last_used: Optional[str] = None
    """ISO timestamp of last use."""

    description: str = ""
    """Optional description."""

    tags: list[str] = field(default_factory=list)
    """Tags for organization."""

    user_agent: Optional[str] = None
    """Custom user agent."""

    proxy: Optional[str] = None
    """Proxy URL."""

    fingerprint_id: Optional[str] = None
    """Associated fingerprint ID."""

    extensions: list[str] = field(default_factory=list)
    """Installed extension paths."""

    preferences: dict[str, Any] = field(default_factory=dict)
    """Custom browser preferences."""

    state: ProfileState = ProfileState.IDLE
    """Current state."""

    lock_pid: Optional[int] = None
    """PID of process holding the lock."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "description": self.description,
            "tags": self.tags,
            "user_agent": self.user_agent,
            "proxy": self.proxy,
            "fingerprint_id": self.fingerprint_id,
            "extensions": self.extensions,
            "preferences": self.preferences,
            "state": self.state.value,
            "lock_pid": self.lock_pid,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileMetadata":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
            last_used=data.get("last_used"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            user_agent=data.get("user_agent"),
            proxy=data.get("proxy"),
            fingerprint_id=data.get("fingerprint_id"),
            extensions=data.get("extensions", []),
            preferences=data.get("preferences", {}),
            state=ProfileState(data.get("state", "idle")),
            lock_pid=data.get("lock_pid"),
        )


@dataclass
class ProfileConfig:
    """Configuration for creating a new profile."""

    name: str
    """Profile name."""

    description: str = ""
    """Optional description."""

    tags: list[str] = field(default_factory=list)
    """Tags for organization."""

    user_agent: Optional[str] = None
    """Custom user agent."""

    proxy: Optional[str] = None
    """Proxy URL."""

    fingerprint: Optional["Fingerprint"] = None
    """Browser fingerprint."""

    extensions: list[str] = field(default_factory=list)
    """Extension paths to install."""

    preferences: dict[str, Any] = field(default_factory=dict)
    """Custom browser preferences."""

    copy_from: Optional[str] = None
    """Profile ID to copy data from."""


class BrowserProfile:
    """Represents a browser profile with persistent user data.

    A profile contains:
    - User data directory (cookies, cache, history, etc.)
    - Configuration (user agent, proxy, fingerprint)
    - Extensions
    - Custom preferences

    Example:
        # Create profile manager
        profiles = ProfileManager()

        # Create new profile
        profile = await profiles.create(ProfileConfig(
            name="Work",
            user_agent="...",
            proxy="http://proxy:8080",
        ))

        # Use profile with browser
        async with Browser(profile=profile) as browser:
            page = await browser.new_page()
            # ... profile data persists across sessions

        # List profiles
        for p in profiles.list_all():
            print(p.name)

        # Delete profile
        await profiles.delete(profile.id)
    """

    def __init__(
        self,
        path: Path,
        metadata: ProfileMetadata,
    ) -> None:
        """Initialize browser profile.

        Args:
            path: Path to profile directory.
            metadata: Profile metadata.
        """
        self._path = path
        self._metadata = metadata
        self._lock_file: Optional[Path] = None

    @property
    def id(self) -> str:
        """Profile ID."""
        return self._metadata.id

    @property
    def name(self) -> str:
        """Profile name."""
        return self._metadata.name

    @property
    def path(self) -> Path:
        """Profile directory path."""
        return self._path

    @property
    def user_data_dir(self) -> str:
        """User data directory for browser."""
        return str(self._path / "user_data")

    @property
    def metadata(self) -> ProfileMetadata:
        """Profile metadata."""
        return self._metadata

    @property
    def state(self) -> ProfileState:
        """Current state."""
        return self._metadata.state

    @property
    def is_locked(self) -> bool:
        """Whether profile is locked."""
        return self._metadata.state == ProfileState.LOCKED

    @property
    def is_active(self) -> bool:
        """Whether profile is active."""
        return self._metadata.state == ProfileState.ACTIVE

    def get_preferences(self) -> dict[str, Any]:
        """Get browser preferences.

        Returns:
            Preferences dictionary.
        """
        prefs_file = self._path / "preferences.json"
        if prefs_file.exists():
            with open(prefs_file) as f:
                return json.load(f)
        return self._metadata.preferences.copy()

    def set_preferences(self, preferences: dict[str, Any]) -> None:
        """Set browser preferences.

        Args:
            preferences: Preferences to set.
        """
        self._metadata.preferences.update(preferences)

        prefs_file = self._path / "preferences.json"
        with open(prefs_file, "w") as f:
            json.dump(self._metadata.preferences, f, indent=2)

    def get_launch_args(self) -> list[str]:
        """Get browser launch arguments for this profile.

        Returns:
            List of command line arguments.
        """
        args = [f"--user-data-dir={self.user_data_dir}"]

        if self._metadata.proxy:
            args.append(f"--proxy-server={self._metadata.proxy}")

        return args

    async def acquire_lock(self) -> bool:
        """Acquire exclusive lock on profile.

        Returns:
            True if lock acquired, False if already locked.
        """
        lock_file = self._path / ".lock"

        if lock_file.exists():
            # Check if locking process is still alive
            try:
                with open(lock_file) as f:
                    data = json.load(f)
                    pid = data.get("pid")
                    if pid and self._is_process_alive(pid):
                        return False
            except (json.JSONDecodeError, OSError):
                pass

        # Create lock file
        with open(lock_file, "w") as f:
            json.dump({"pid": os.getpid(), "timestamp": datetime.utcnow().isoformat()}, f)

        self._lock_file = lock_file
        self._metadata.state = ProfileState.ACTIVE
        self._metadata.lock_pid = os.getpid()
        self._save_metadata()

        return True

    async def release_lock(self) -> None:
        """Release lock on profile."""
        if self._lock_file and self._lock_file.exists():
            try:
                self._lock_file.unlink()
            except OSError:
                pass

        self._lock_file = None
        self._metadata.state = ProfileState.IDLE
        self._metadata.lock_pid = None
        self._metadata.last_used = datetime.utcnow().isoformat()
        self._save_metadata()

    def _is_process_alive(self, pid: int) -> bool:
        """Check if a process is alive.

        Args:
            pid: Process ID.

        Returns:
            True if process exists.
        """
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _save_metadata(self) -> None:
        """Save metadata to file."""
        metadata_file = self._path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(self._metadata.to_dict(), f, indent=2)

    async def export(self, output_path: str) -> str:
        """Export profile to a zip file.

        Args:
            output_path: Output file path.

        Returns:
            Path to created zip file.
        """
        import zipfile

        output = Path(output_path)
        if not output.suffix:
            output = output.with_suffix(".zip")

        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self._path):
                # Skip cache directories
                dirs[:] = [d for d in dirs if d not in ("Cache", "Code Cache", "GPUCache")]

                for file in files:
                    file_path = Path(root) / file
                    arc_name = file_path.relative_to(self._path)
                    zf.write(file_path, arc_name)

        return str(output)

    def __repr__(self) -> str:
        return f"BrowserProfile(id={self.id!r}, name={self.name!r}, state={self.state.value})"


class ProfileManager:
    """Manages browser profiles.

    Handles creation, deletion, import/export, and lifecycle
    of browser profiles.

    Example:
        profiles = ProfileManager()

        # Create profile
        profile = await profiles.create(ProfileConfig(name="Test"))

        # Get profile
        profile = profiles.get("profile-id")

        # List all profiles
        for p in profiles.list_all():
            print(p.name)

        # Delete profile
        await profiles.delete("profile-id")
    """

    def __init__(
        self,
        profiles_dir: Optional[Path] = None,
    ) -> None:
        """Initialize profile manager.

        Args:
            profiles_dir: Directory for storing profiles.
        """
        self._profiles_dir = profiles_dir or DEFAULT_PROFILES_DIR
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: dict[str, BrowserProfile] = {}
        self._loaded = False

    @property
    def profiles_dir(self) -> Path:
        """Profiles directory path."""
        return self._profiles_dir

    def _generate_id(self, name: str) -> str:
        """Generate unique profile ID.

        Args:
            name: Profile name.

        Returns:
            Unique ID.
        """
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{name}{timestamp}{os.getpid()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    def _load_profiles(self) -> None:
        """Load all profiles from disk."""
        if self._loaded:
            return

        for profile_dir in self._profiles_dir.iterdir():
            if not profile_dir.is_dir():
                continue

            metadata_file = profile_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file) as f:
                    data = json.load(f)
                    metadata = ProfileMetadata.from_dict(data)

                    # Reset state on load (process might have crashed)
                    if metadata.state != ProfileState.IDLE:
                        lock_file = profile_dir / ".lock"
                        if lock_file.exists():
                            try:
                                with open(lock_file) as lf:
                                    lock_data = json.load(lf)
                                    pid = lock_data.get("pid")
                                    if not self._is_process_alive(pid):
                                        lock_file.unlink()
                                        metadata.state = ProfileState.IDLE
                            except (json.JSONDecodeError, OSError):
                                lock_file.unlink()
                                metadata.state = ProfileState.IDLE

                    profile = BrowserProfile(profile_dir, metadata)
                    self._profiles[metadata.id] = profile

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load profile from {profile_dir}: {e}")

        self._loaded = True

    def _is_process_alive(self, pid: Optional[int]) -> bool:
        """Check if process is alive."""
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    async def create(
        self,
        config: ProfileConfig,
    ) -> BrowserProfile:
        """Create a new profile.

        Args:
            config: Profile configuration.

        Returns:
            Created profile.
        """
        self._load_profiles()

        profile_id = self._generate_id(config.name)
        profile_dir = self._profiles_dir / profile_id
        profile_dir.mkdir(parents=True, exist_ok=True)

        # Create user data directory
        user_data_dir = profile_dir / "user_data"
        user_data_dir.mkdir(exist_ok=True)

        # Copy from existing profile if specified
        if config.copy_from:
            source = self._profiles.get(config.copy_from)
            if source:
                shutil.copytree(
                    source.user_data_dir,
                    str(user_data_dir),
                    dirs_exist_ok=True,
                )

        # Create metadata
        metadata = ProfileMetadata(
            id=profile_id,
            name=config.name,
            created_at=datetime.utcnow().isoformat(),
            description=config.description,
            tags=config.tags,
            user_agent=config.user_agent,
            proxy=config.proxy,
            extensions=config.extensions,
            preferences=config.preferences,
        )

        # Save fingerprint if provided
        if config.fingerprint:
            fp_file = profile_dir / "fingerprint.json"
            with open(fp_file, "w") as f:
                json.dump(config.fingerprint.model_dump(), f, indent=2)
            metadata.fingerprint_id = profile_id

        # Save metadata
        metadata_file = profile_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Save preferences
        if config.preferences:
            prefs_file = profile_dir / "preferences.json"
            with open(prefs_file, "w") as f:
                json.dump(config.preferences, f, indent=2)

        profile = BrowserProfile(profile_dir, metadata)
        self._profiles[profile_id] = profile

        logger.info(f"Created profile: {config.name} ({profile_id})")
        return profile

    def get(self, profile_id: str) -> Optional[BrowserProfile]:
        """Get profile by ID.

        Args:
            profile_id: Profile ID.

        Returns:
            Profile or None if not found.
        """
        self._load_profiles()
        return self._profiles.get(profile_id)

    def get_by_name(self, name: str) -> Optional[BrowserProfile]:
        """Get profile by name.

        Args:
            name: Profile name.

        Returns:
            First matching profile or None.
        """
        self._load_profiles()
        for profile in self._profiles.values():
            if profile.name == name:
                return profile
        return None

    def list_all(self) -> list[BrowserProfile]:
        """List all profiles.

        Returns:
            List of all profiles.
        """
        self._load_profiles()
        return list(self._profiles.values())

    def list_by_tag(self, tag: str) -> list[BrowserProfile]:
        """List profiles with a specific tag.

        Args:
            tag: Tag to filter by.

        Returns:
            List of matching profiles.
        """
        self._load_profiles()
        return [p for p in self._profiles.values() if tag in p.metadata.tags]

    def list_available(self) -> list[BrowserProfile]:
        """List profiles that are not locked.

        Returns:
            List of available profiles.
        """
        self._load_profiles()
        return [p for p in self._profiles.values() if not p.is_locked]

    async def delete(self, profile_id: str) -> bool:
        """Delete a profile.

        Args:
            profile_id: Profile to delete.

        Returns:
            True if deleted successfully.
        """
        self._load_profiles()

        profile = self._profiles.get(profile_id)
        if not profile:
            return False

        if profile.is_locked:
            raise RuntimeError(f"Cannot delete locked profile: {profile_id}")

        # Remove directory
        try:
            shutil.rmtree(profile.path)
        except OSError as e:
            logger.error(f"Failed to delete profile directory: {e}")
            return False

        del self._profiles[profile_id]
        logger.info(f"Deleted profile: {profile.name} ({profile_id})")
        return True

    async def import_profile(
        self,
        zip_path: str,
        name: Optional[str] = None,
    ) -> BrowserProfile:
        """Import profile from zip file.

        Args:
            zip_path: Path to zip file.
            name: Optional new name for profile.

        Returns:
            Imported profile.
        """
        import zipfile

        self._load_profiles()

        # Extract to temp directory first
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)

            # Read metadata
            metadata_file = Path(temp_dir) / "metadata.json"
            if not metadata_file.exists():
                raise ValueError("Invalid profile archive: missing metadata.json")

            with open(metadata_file) as f:
                data = json.load(f)
                old_metadata = ProfileMetadata.from_dict(data)

            # Generate new ID
            profile_name = name or old_metadata.name
            profile_id = self._generate_id(profile_name)
            profile_dir = self._profiles_dir / profile_id

            # Copy files
            shutil.copytree(temp_dir, profile_dir)

            # Update metadata
            new_metadata = ProfileMetadata(
                id=profile_id,
                name=profile_name,
                created_at=datetime.utcnow().isoformat(),
                description=old_metadata.description,
                tags=old_metadata.tags,
                user_agent=old_metadata.user_agent,
                proxy=old_metadata.proxy,
                fingerprint_id=old_metadata.fingerprint_id,
                extensions=old_metadata.extensions,
                preferences=old_metadata.preferences,
                state=ProfileState.IDLE,
            )

            metadata_file = profile_dir / "metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(new_metadata.to_dict(), f, indent=2)

            profile = BrowserProfile(profile_dir, new_metadata)
            self._profiles[profile_id] = profile

            logger.info(f"Imported profile: {profile_name} ({profile_id})")
            return profile

    async def duplicate(
        self,
        profile_id: str,
        new_name: Optional[str] = None,
    ) -> BrowserProfile:
        """Duplicate an existing profile.

        Args:
            profile_id: Profile to duplicate.
            new_name: Name for new profile.

        Returns:
            New profile.
        """
        self._load_profiles()

        source = self._profiles.get(profile_id)
        if not source:
            raise ValueError(f"Profile not found: {profile_id}")

        return await self.create(
            ProfileConfig(
                name=new_name or f"{source.name} (Copy)",
                description=source.metadata.description,
                tags=source.metadata.tags,
                user_agent=source.metadata.user_agent,
                proxy=source.metadata.proxy,
                extensions=source.metadata.extensions,
                preferences=source.metadata.preferences,
                copy_from=profile_id,
            )
        )

    def cleanup_stale_locks(self) -> int:
        """Clean up stale locks from crashed processes.

        Returns:
            Number of locks cleaned.
        """
        self._load_profiles()
        cleaned = 0

        for profile in self._profiles.values():
            if profile.is_locked:
                lock_file = profile.path / ".lock"
                if lock_file.exists():
                    try:
                        with open(lock_file) as f:
                            data = json.load(f)
                            pid = data.get("pid")
                            if not self._is_process_alive(pid):
                                lock_file.unlink()
                                profile._metadata.state = ProfileState.IDLE
                                profile._metadata.lock_pid = None
                                profile._save_metadata()
                                cleaned += 1
                    except (json.JSONDecodeError, OSError):
                        lock_file.unlink()
                        profile._metadata.state = ProfileState.IDLE
                        cleaned += 1

        return cleaned

    def __len__(self) -> int:
        self._load_profiles()
        return len(self._profiles)

    def __iter__(self):
        self._load_profiles()
        return iter(self._profiles.values())

    def __contains__(self, profile_id: str) -> bool:
        self._load_profiles()
        return profile_id in self._profiles


class TemporaryProfile:
    """Context manager for temporary profiles.

    Creates a profile that is automatically deleted when done.

    Example:
        async with TemporaryProfile() as profile:
            async with Browser(profile=profile) as browser:
                # ... use browser
        # Profile is deleted
    """

    def __init__(
        self,
        manager: Optional[ProfileManager] = None,
        config: Optional[ProfileConfig] = None,
    ) -> None:
        """Initialize temporary profile.

        Args:
            manager: Profile manager to use.
            config: Optional configuration.
        """
        self._manager = manager or ProfileManager()
        self._config = config or ProfileConfig(name="temp")
        self._profile: Optional[BrowserProfile] = None

    async def __aenter__(self) -> BrowserProfile:
        self._profile = await self._manager.create(self._config)
        return self._profile

    async def __aexit__(self, *args: Any) -> None:
        if self._profile:
            await self._manager.delete(self._profile.id)


__all__ = [
    "BrowserProfile",
    "ProfileConfig",
    "ProfileManager",
    "ProfileMetadata",
    "ProfileState",
    "TemporaryProfile",
]
