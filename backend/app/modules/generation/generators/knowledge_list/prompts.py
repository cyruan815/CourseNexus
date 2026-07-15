from app.modules.generation.generators.knowledge_list.schemas import KnowledgeListParameters
from app.modules.material_context.schemas import MaterialGenerationContext


def build_knowledge_prompt(context: MaterialGenerationContext, *, parameters: KnowledgeListParameters) -> str:
    return (
        "Generate the final knowledge-point list using only the complete material context below. "
        f"Return at most {parameters.item_count} unique items. Extraction focus: {parameters.extraction_focus}. "
        f"Minimum importance: {parameters.minimum_importance}. User focus: {parameters.focus or 'none'}. "
        "Return a concise Simplified Chinese topic_title (30 characters maximum). For one chapter, use its chapter title; "
        "for multiple chapters, summarize their shared topic. Do not include the feature name, counts, or parentheses. "
        "Prioritize concepts, principles, formula conditions, and common misconceptions. Do not turn ordinary headings, "
        "document labels, or generic overview phrases into knowledge items. Preserve a useful learning order and "
        "do not return source IDs or citations.\n\n"
        + context.text
    )
