from app.modules.generation.generators.mindmap.schemas import MindmapParameters
from app.modules.material_context.schemas import MaterialGenerationContext


def build_mindmap_prompt(context: MaterialGenerationContext, *, parameters: MindmapParameters) -> str:
    return (
        "Generate one complete mindmap graph using only the complete material context below. "
        f"Center topic: {parameters.center_topic or 'infer from material'}. "
        f"Maximum nodes: {parameters.max_nodes}. Maximum depth: {parameters.max_depth}. "
        f"Related cross-links allowed: {parameters.include_cross_links}. "
        "Use concise labels and place useful detail in summaries. Avoid generic meta nodes such as course material, "
        "main content, overview, or key points unless that phrase is itself a defined subject concept. "
        "Return exactly one level-1 root, unique node IDs, valid child edges, no cycles, and no source IDs or citations.\n\n"
        + context.text
    )
