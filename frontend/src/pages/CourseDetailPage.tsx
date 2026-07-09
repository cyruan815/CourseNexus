import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { ApiError } from "../api/errors";
import { fetchCourse } from "../features/courses/api";
import { CourseHeader } from "../features/courses/CourseHeader";
import type { Course } from "../types/course";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return "课程加载失败";
}

function WorkspaceSection({ label }: { label: string }) {
  return (
    <section aria-label={label}>
      <h2>{label}</h2>
    </section>
  );
}

export function CourseDetailPage() {
  const { courseId } = useParams();
  const [course, setCourse] = useState<Course | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let ignore = false;

    if (!courseId) {
      setError("课程不存在");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    fetchCourse(courseId)
      .then((nextCourse) => {
        if (!ignore) {
          setCourse(nextCourse);
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
  }, [courseId]);

  if (isLoading) {
    return <p role="status">正在加载课程...</p>;
  }

  if (error || !course) {
    return <p role="alert">{error ?? "课程不存在"}</p>;
  }

  return (
    <main>
      <CourseHeader course={course} />
      <WorkspaceSection label="资料区" />
      <WorkspaceSection label="问答区" />
      <WorkspaceSection label="生成内容区" />
      <WorkspaceSection label="学习计划入口" />
    </main>
  );
}
