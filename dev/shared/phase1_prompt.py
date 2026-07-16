"""Shared Phase 1 prompt: Julius Caesar / Republic → Empire comic panel."""

PROMPT = (
    "Comic-book panel, bold ink and muted Roman color, Julius Caesar standing "
    "before the Senate as the Roman Republic gives way to imperial power; "
    "marble columns, tense senators, dramatic chiaroscuro; historically "
    "suggestive costume (laurel, toga/armor); no modern text, no speech bubbles, "
    "single heroic panel composition."
)

OUTPUT_FILENAME = "julius_caesar_republic_to_empire.png"

# Shared panel size (portrait comic-ish); plan uses 800x1280.
IMAGE_WIDTH = 800
IMAGE_HEIGHT = 1280
# Gemini imageConfig: closest supported ratio to 800:1280 (exact pixels via resize).
IMAGE_ASPECT_RATIO = "2:3"

FLUX_WIDTH = IMAGE_WIDTH
FLUX_HEIGHT = IMAGE_HEIGHT
FLUX_SEED = 42
FLUX_STEPS = 4
FLUX_GUIDANCE = 0.0
FLUX_MAX_SEQ_LEN = 256

MODEL_FLUX = "black-forest-labs/FLUX.1-schnell"
MODEL_NANO_BANANA = "gemini-3.1-flash-image"

TARGET_VRAM_GB = 12.0
TARGET_INFER_SECONDS = 30.0
