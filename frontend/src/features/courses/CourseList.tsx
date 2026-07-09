import { Link } from "react-router-dom";

import type { Course } from "../../types/course";

interface CourseListProps {
  courses: Course[];
  isLoading?: boolean;
  error?: string | null;
}

export function CourseList({ courses, isLoading = false, error = null }: CourseListProps) {
  if (isLoading) {
    return <p role="status">正在加载课程...</p>;
  }

  if (error) {
    return <p role="alert">课程加载失败：{error}</p>;
  }

  if (courses.length === 0) {
    return <p>还没有课程</p>;
  }

  return (
    <ul aria-label="课程列表">
      {courses.map((course) => (
        <li key={course.id}>
          <Link to={`/courses/${course.id}`}>{course.name}</Link>
          {course.teacher ? <span>{course.teacher}</span> : null}
          {course.term ? <span>{course.term}</span> : null}
        </li>
      ))}
    </ul>
  );
}
