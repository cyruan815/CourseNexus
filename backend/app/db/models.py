"""Import all SQLAlchemy models so Alembic can discover metadata."""

from app.modules.checkins.models import CheckinRecord
from app.modules.course_qa.models import Conversation, Message, SourceCitation
from app.modules.courses.models import Course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialFolder
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.users.models import User

__all__ = [
    "AIGeneratedContent",
    "CheckinRecord",
    "Conversation",
    "Course",
    "CourseMaterial",
    "MaterialChunk",
    "MaterialFolder",
    "Message",
    "SourceCitation",
    "StudyPlan",
    "StudySubTask",
    "StudyTask",
    "User",
]
