from app.modules.generation.generators.flashcard.schemas import FlashcardParameters
from app.modules.material_context.schemas import MaterialGenerationContext


def build_flashcard_prompt(context: MaterialGenerationContext, *, parameters: FlashcardParameters) -> str:
    return (
        "Generate the final flashcard set using only the complete material context below. "
        f"Return at most {parameters.card_count} atomic cards. Style: {parameters.card_style}. "
        f"Include formulas: {parameters.include_formulas}. Focus: {parameters.focus or 'none'}. "
        "Do not return source IDs or citations.\n\n"
        + context.text
    )
