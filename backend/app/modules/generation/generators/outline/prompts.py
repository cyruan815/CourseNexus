from app.modules.generation.generators.outline.schemas import OutlineParameters
from app.modules.material_context.schemas import MaterialGenerationContext


def build_outline_prompt(context: MaterialGenerationContext, *, parameters: OutlineParameters) -> str:
    return (
        "Generate the final review outline using only the complete material context below. "
        f"Return at most {parameters.section_count} sections in the requested order. "
        f"Organization: {parameters.organization}. Review goal: {parameters.review_goal or 'none'}. "
        f"Detail: {parameters.detail_level}. Do not return source IDs, source order keys, or citations.\n\n"
        + context.text
    )
