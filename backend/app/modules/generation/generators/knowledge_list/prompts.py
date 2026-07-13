from app.modules.generation.generators.knowledge_list.schemas import KnowledgeListParameters
from app.modules.material_context.schemas import MaterialGenerationContext


def build_knowledge_prompt(context: MaterialGenerationContext, *, parameters: KnowledgeListParameters) -> str:
    return (
        "Generate the final knowledge-point list using only the complete material context below. "
        f"Return at most {parameters.item_count} unique items. Extraction focus: {parameters.extraction_focus}. "
        f"Minimum importance: {parameters.minimum_importance}. User focus: {parameters.focus or 'none'}. "
        "Preserve a useful learning order and do not return source IDs or citations.\n\n"
        + context.text
    )
