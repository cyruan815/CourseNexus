import { useEffect, useState } from "react";

import { ApiError } from "../api/errors";
import { listCourses } from "../features/courses/api";
import { CourseList } from "../features/courses/CourseList";
import type { Course } from "../types/course";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return "课程加载失败";
}

export function HomePage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let ignore = false;

    listCourses()
      .then((nextCourses) => {
        if (!ignore) {
          setCourses(nextCourses);
        }
      })
      .catch((nextError: unknown) => {
        if (!ignore) {
          setError(errorMessage(nextError));
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  return (
    <main>
      <h1>CourseNexus</h1>
      <p>课程工作台</p>
      <CourseList courses={courses} error={error} isLoading={isLoading} />
    </main>
  );
}
