from app.modules.generation.generators.flashcard.schemas import FlashcardParameters
from app.modules.material_context.schemas import MaterialGenerationContext


def build_flashcard_prompt(context: MaterialGenerationContext, *, parameters: FlashcardParameters) -> str:
    return (
        "Generate the final flashcard set using only the complete material context below. "
        f"Return at most {parameters.card_count} atomic cards. Style: {parameters.card_style}. "
        f"Include formulas: {parameters.include_formulas}. Focus: {parameters.focus or 'none'}. "
        "Return a concise Simplified Chinese topic_title (30 characters maximum). For one chapter, use its chapter title; "
        "for multiple chapters, summarize their shared topic. Do not include the feature name, counts, or parentheses. "
        "Each card must test one atomic concept with a standalone front and a concise back. "
        "Avoid outline paragraphs and duplicate prompts. Add an optional explanation only for context or a common misconception. "
        "Do not return source IDs or citations.\n\n"
        + context.text
    )
