"""Phase 2 style definition strings and Caesar-story test subjects.

People-free subjects drawn from the Julius Caesar Ides of March betrayal story.
Style strings are candidates for the series lock; characters belong in Phase 3.

Step 2.1: style bake-off across STYLES × SUBJECTS × MODELS.
Step 2.2: seed-grid stability on storybook_gouache with DETAIL_LEVELS.
"""

from __future__ import annotations

from typing import Any

# Panel size matches Phase 1 for fair comparison (import-free copy to avoid coupling).
IMAGE_WIDTH = 800
IMAGE_HEIGHT = 1280
IMAGE_ASPECT_RATIO = "2:3"

MODEL_FLUX = "black-forest-labs/FLUX.1-schnell"
MODEL_NANO_BANANA = "gemini-3.1-flash-image"

# Shared prompt guardrails appended to every generation.
SUBJECT_NEGATIVES = (
    "no people, no figures, no faces, no text, no border, no speech bubbles, "
    "no blood, no gore, no weapons raised, no graphic injury"
)

# Step 2.2 — locked style + seed grid over betrayal_aftermath.
# Default matrix uses one subject prompt only (9 seeds × 2 models = 18).
# Extra DETAIL_LEVELS remain available via run_step22(detail_levels=[...]).
STEP22_STYLE_ID = "storybook_gouache"
STEP22_DEFAULT_DETAIL_ID = "d3_medium"
SEEDS = tuple(range(9))
SEED_SUPPORTED_MODELS = frozenset({"flux_fal"})

STYLES: dict[str, str] = {
    "storybook_gouache": (
        "warm painterly storybook illustration, soft gouache and colored-pencil "
        "texture, gentle golden lamplight, rounded forms, cozy bedtime-story mood, "
        "muted historical palette, NOT anime, NOT manga, no cel shading, "
        "no hard ink outlines, no photorealism"
    ),
    "watercolor_wash": (
        "soft wet watercolor children's book illustration, visible paper tooth, "
        "gentle pigment blooms and soft edges, quiet diffused daylight, "
        "rounded calm forms, muted historical palette, cozy bedtime-story mood, "
        "NOT anime, NOT manga, no cel shading, no hard ink outlines, no photorealism"
    ),
    "pastel_chalk": (
        "children's book illustration in soft dry pastel and chalk sticks on textured "
        "pastel paper, heavy chalk dust and smudged pigment, visible pastel strokes "
        "and powdery grain, soft feathered edges, warm lamplight, rounded forms, "
        "cozy bedtime-story mood, muted historical palette, "
        "NOT oil paint, NOT digital smooth rendering, NOT anime, NOT manga, "
        "no cel shading, no hard ink outlines, no photorealism"
    ),
    "ink_wash_sepia": (
        "warm sepia ink wash with light watercolor tint, soft brush washes, "
        "gentle graphic forms without hard outlines, cozy bedtime-story mood, "
        "strictly muted sepia ochre-and-ivory monochrome palette throughout, "
        "no full-color sky, "
        "NOT anime, NOT manga, no cel shading, no hard black outlines, no photorealism"
    ),
    "colored_pencil_cozy": (
        "intimate colored-pencil children's book illustration, soft hatching "
        "and layered pencil texture, close golden lamplight, rounded forms, "
        "cozy bedtime-story mood, muted historical palette, "
        "NOT anime, NOT manga, no cel shading, no hard ink outlines, no photorealism"
    ),
}

SUBJECTS: dict[str, str] = {
    "senate_interior": (
        "interior of the Senate meeting hall (Curia of Pompey) in mid-1st-century BC "
        "Rome, empty tiered wooden benches facing a raised dais, marble columns, "
        "plain stone floor, cool quiet morning light from high openings, "
        "restrained Republican architecture, no people"
    ),
    "betrayal_aftermath": (
        "aftermath of the Ides of March betrayal rendered symbolically: "
        "Caesar's laurel wreath fallen on marble steps beside a dropped scroll, "
        "long dramatic shadows across empty stone, solemn quiet, "
        "no people, no blood, no weapons"
    ),
    "forum_dusk": (
        "the Roman Forum at dusk, empty streets and market stalls shut for the night, "
        "guttering torchlight, long uneasy shadows, quiet city-after mood, no people"
    ),
}

MODELS: dict[str, dict[str, str]] = {
    "flux_fal": {
        "backend": "hf",
        "provider": "fal-ai",
        "model_id": MODEL_FLUX,
    },
    "nano_banana": {
        "backend": "google",
        "provider": "google",
        "model_id": MODEL_NANO_BANANA,
    },
}

# Step 2.2 — 3 detail levels only (cost cap: 9 seeds × 1 subject × 3 = 27/model).
# d1 max detail → d3 medium (Step 2.1 baseline) → d5 min.
DETAIL_LEVELS: dict[str, str] = {
    "d1_max": (
        "aftermath of the Ides of March betrayal rendered symbolically: "
        "Caesar's green laurel wreath fallen askew on cool pale marble steps, "
        "leaves still vivid olive-green with soft gouache texture, "
        "beside an ivory cream parchment scroll with a broken wax seal, "
        "long dramatic shadows stretching across empty stone, "
        "solemn quiet morning light, restrained Republican architecture, "
        "no people, no blood, no weapons"
    ),
    "d3_medium": (
        "aftermath of the Ides of March betrayal rendered symbolically: "
        "Caesar's laurel wreath fallen on marble steps beside a dropped scroll, "
        "long dramatic shadows across empty stone, solemn quiet, "
        "no people, no blood, no weapons"
    ),
    "d5_min": (
        "Ides of March aftermath: fallen laurel and scroll on empty marble steps"
    ),
}

# Rank 1 = most detailed … 3 = least (for CSV sorting / comparison).
DETAIL_RANKS: dict[str, int] = {
    "d1_max": 1,
    "d3_medium": 2,
    "d5_min": 3,
}

STYLE_IDS = tuple(STYLES.keys())
SUBJECT_IDS = tuple(SUBJECTS.keys())
MODEL_KEYS = tuple(MODELS.keys())
DETAIL_IDS = tuple(DETAIL_LEVELS.keys())


def build_prompt(style_id: str, subject_id: str) -> str:
    """Assemble style + subject + shared negatives into one generation prompt."""
    if style_id not in STYLES:
        raise KeyError(f"unknown style_id {style_id!r}; expected one of {STYLE_IDS}")
    if subject_id not in SUBJECTS:
        raise KeyError(
            f"unknown subject_id {subject_id!r}; expected one of {SUBJECT_IDS}"
        )
    return (
        f"{STYLES[style_id]}. Subject: {SUBJECTS[subject_id]}. "
        f"Single illustration. Negatives: {SUBJECT_NEGATIVES}."
    )


def build_prompt_step22(detail_id: str, style_id: str = STEP22_STYLE_ID) -> str:
    """Assemble locked style + detail-level subject + shared negatives."""
    if style_id not in STYLES:
        raise KeyError(f"unknown style_id {style_id!r}; expected one of {STYLE_IDS}")
    if detail_id not in DETAIL_LEVELS:
        raise KeyError(
            f"unknown detail_id {detail_id!r}; expected one of {DETAIL_IDS}"
        )
    return (
        f"{STYLES[style_id]}. Subject: {DETAIL_LEVELS[detail_id]}. "
        f"Single illustration. Negatives: {SUBJECT_NEGATIVES}."
    )


def output_filename(style_id: str, subject_id: str, model_key: str) -> str:
    return f"{style_id}__{subject_id}__{model_key}.png"


def output_filename_step22(
    detail_id: str,
    model_key: str,
    seed: int,
    style_id: str = STEP22_STYLE_ID,
) -> str:
    return f"{style_id}__{detail_id}__{model_key}__seed{seed}.png"


def model_supports_seed(model_key: str) -> bool:
    return model_key in SEED_SUPPORTED_MODELS


def freeze_config() -> dict[str, Any]:
    """Snapshot used for styles.json in a Step 2.1 run directory."""
    return {
        "step": "2.1",
        "story": "julius_caesar_ides_of_march_betrayal",
        "image_width": IMAGE_WIDTH,
        "image_height": IMAGE_HEIGHT,
        "image_aspect_ratio": IMAGE_ASPECT_RATIO,
        "styles": dict(STYLES),
        "subjects": dict(SUBJECTS),
        "models": {k: dict(v) for k, v in MODELS.items()},
        "subject_negatives": SUBJECT_NEGATIVES,
    }


def freeze_config_step22() -> dict[str, Any]:
    """Snapshot used for styles.json in a Step 2.2 run directory."""
    return {
        "step": "2.2",
        "story": "julius_caesar_ides_of_march_betrayal",
        "style_id": STEP22_STYLE_ID,
        "style_string": STYLES[STEP22_STYLE_ID],
        "subject_base": "betrayal_aftermath",
        "matrix_per_model": "9 seeds × 1 subject × 3 detail levels = 27",
        "image_width": IMAGE_WIDTH,
        "image_height": IMAGE_HEIGHT,
        "image_aspect_ratio": IMAGE_ASPECT_RATIO,
        "detail_levels": dict(DETAIL_LEVELS),
        "detail_ranks": dict(DETAIL_RANKS),
        "seeds": list(SEEDS),
        "seed_supported_models": sorted(SEED_SUPPORTED_MODELS),
        "models": {k: dict(v) for k, v in MODELS.items()},
        "subject_negatives": SUBJECT_NEGATIVES,
    }
