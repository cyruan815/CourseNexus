import type { Course } from "../../types/course";

interface CourseHeaderProps {
  course: Course;
}

export function CourseHeader({ course }: CourseHeaderProps) {
  return (
    <header>
      <h1>{course.name}</h1>
      {course.description ? <p>{course.description}</p> : null}
      <dl>
        {course.teacher ? (
          <>
            <dt>教师</dt>
            <dd>{course.teacher}</dd>
          </>
        ) : null}
        {course.term ? (
          <>
            <dt>学期</dt>
            <dd>{course.term}</dd>
          </>
        ) : null}
      </dl>
    </header>
  );
}
