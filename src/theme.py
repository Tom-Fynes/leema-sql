"""Nebula Nights theme for Leema SQL IDE."""

from textual.theme import Theme

NEBULA_NIGHTS = Theme(
    name="nebula-nights",
    dark=True,
    primary="#DD7596",
    secondary="#9F7EBE",
    accent="#63C5EA",
    warning="#ECDA90",
    error="#D05786",
    success="#94FBAB",
    foreground="#B7C3F3",
    background="#404E5C",
    surface="#363E4A",
    panel="#2E3A48",
    boost="#4F6272",
    variables={
        # Activity bar
        "activity-bar-background": "#2E3A48",
        "activity-bar-foreground": "#B7C3F3",
        "activity-bar-inactive-foreground": "#4F6272",
        # Status bar
        "status-bar-background": "#2E3A48",
        "status-bar-foreground": "#B7C3F3",
        # Terminal ANSI colours
        "terminal-ansi-black": "#363E4A",
        "terminal-ansi-blue": "#B8E1FF",
        "terminal-ansi-cyan": "#A9FFF7",
        "terminal-ansi-green": "#94FBAB",
        "terminal-ansi-magenta": "#BCB6FF",
        "terminal-ansi-red": "#D05786",
        "terminal-ansi-white": "#B7C3F3",
        "terminal-ansi-yellow": "#DD7596",
        # Highlights
        "editor-line-highlight": "#4F627233",
        "editor-selection": "#4F627266",
        "word-highlight": "#BCB6FF33",
        "word-highlight-strong": "#B8E1FF33",
        # Bracket colours
        "bracket-1": "#63C5EA",
        "bracket-2": "#9F7EBE",
        "bracket-3": "#83AFDF",
        "bracket-4": "#BCB6FF",
        "bracket-5": "#B8E1FF",
        "bracket-6": "#A9FFF7",
    },
)
