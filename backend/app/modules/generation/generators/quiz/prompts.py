from app.modules.generation.generators.quiz.schemas import QuizParameters
from app.modules.material_context.schemas import MaterialGenerationContext


def build_quiz_prompt(context: MaterialGenerationContext, *, parameters: QuizParameters) -> str:
    return (
        "Generate the final course quiz using only the complete material context below. "
        f"Return exactly {parameters.question_count} unique single-choice questions when the material supports it. "
        "Test conceptual understanding, distinctions, and simple application instead of copying source sentences. "
        "Each question must have options A-D, one unambiguous correct answer, plausible distractors, "
        "a concise overall explanation, and an optional short hint that guides without revealing the answer. "
        "Every option must include one one-sentence explanation. For the correct option, explain the decisive detail. "
        "For each incorrect option, explain why that specific option is wrong by naming the mistaken concept, scope, condition, cause, or definition in the option itself; "
        "do not reveal the correct answer, do not state the correct conclusion, and do not use generic phrases such as 'does not meet the question requirement' or 'differs from the tested conclusion'. "
        f"Difficulty: {parameters.difficulty}. Focus: {parameters.focus or 'none'}. "
        "Do not return source IDs or citations.\n\n"
        + context.text
    )
