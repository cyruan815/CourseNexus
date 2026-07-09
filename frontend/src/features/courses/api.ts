import { apiRequest } from "../../api/client";
import type { Course } from "../../types/course";

export function listCourses(): Promise<Course[]> {
  return apiRequest<Course[]>("/api/v1/courses");
}

export function fetchCourse(courseId: string): Promise<Course> {
  return apiRequest<Course>(`/api/v1/courses/${courseId}`);
}
