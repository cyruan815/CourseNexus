from app.modules.generation.generators.quiz.schemas import QuizParameters
from app.modules.material_context.schemas import MaterialGenerationContext


def build_quiz_prompt(context: MaterialGenerationContext, *, parameters: QuizParameters) -> str:
    return (
        "Generate the final course quiz using only the complete material context below. "
        f"Return exactly {parameters.question_count} unique single-choice questions when the material supports it. "
        "Each question must have options A-D, one correct answer, and a concise explanation. "
        f"Difficulty: {parameters.difficulty}. Focus: {parameters.focus or 'none'}. "
        "Do not return source IDs or citations.\n\n"
        + context.text
    )
