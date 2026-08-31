from pathlib import Path

from app.models.profile import Profile, ProfileLinks
from app.storage.profile_store import load_profile, save_profile


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "profile" / "profile.yaml"
    profile = Profile(
        name="Jane Doe",
        headline="Building things",
        bio="A short bio.",
        location="Remote",
        avatar="avatar.png",
        links=ProfileLinks(
            linkedin="https://www.linkedin.com/in/janedoe", github="https://github.com/janedoe"
        ),
    )

    save_profile(path, profile)
    loaded = load_profile(path)

    assert loaded == profile


def test_save_profile_output_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    profile = Profile(name="Jane Doe", headline="Building things", bio="A short bio.")

    save_profile(path, profile)
    first = path.read_text(encoding="utf-8")
    save_profile(path, profile)
    second = path.read_text(encoding="utf-8")

    assert first == second


def test_save_profile_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "profile" / "profile.yaml"
    save_profile(path, Profile(name="Jane Doe"))
    assert path.exists()
