"""Render ACE playbook bullets into prompt context."""

from __future__ import annotations

from src.ace.playbook import AceBullet, load_playbook


def render_bullet(bullet: AceBullet, *, include_patterns: bool = True) -> str:
    """Render one enabled ACE bullet as compact prompt text."""
    lines = [f"- {bullet.title}: {bullet.content}"]

    if include_patterns and bullet.positive_pattern:
        lines.append(f"  Use pattern: {bullet.positive_pattern}")

    if include_patterns and bullet.avoid:
        lines.append(f"  Avoid: {bullet.avoid}")

    return "\n".join(lines)


def render_ace_context(
    *,
    playbook_path: str,
    family: str,
    mode: str,
    max_bullets: int = 5,
    include_patterns: bool = True,
) -> str:
    """Render the filtered playbook block prepended to model prompts."""
    playbook = load_playbook(playbook_path)
    bullets = playbook.filter_bullets(
        family=family,
        mode=mode,
        max_bullets=max_bullets,
    )

    if not bullets:
        return ""

    rendered = "\n".join(
        render_bullet(bullet, include_patterns=include_patterns)
        for bullet in bullets
    )

    return (
        "ACE playbook rules learned from validation feedback:\n"
        f"{rendered}\n"
        "Follow these rules, but still return only the required final query.\n"
    )
