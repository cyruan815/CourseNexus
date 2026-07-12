import { apiRequest } from "../../api/client";
import type { Course } from "../../types/course";

export interface CourseMutationPayload {
  name?: string;
  description?: string | null;
  teacher?: string | null;
  term?: string | null;
}

export interface CourseTermOption {
  value: string;
  label: string;
}

export function listCourses(): Promise<Course[]> {
  return apiRequest<Course[]>("/api/v1/courses");
}

export function listCourseTermOptions(): Promise<CourseTermOption[]> {
  return apiRequest<CourseTermOption[]>("/api/v1/course-terms");
}

export function fetchCourse(courseId: string): Promise<Course> {
  return apiRequest<Course>(`/api/v1/courses/${courseId}`);
}

export function createCourse(payload: Required<CourseMutationPayload>): Promise<Course> {
  return apiRequest<Course>("/api/v1/courses", {
    method: "POST",
    body: payload,
  });
}

export function updateCourse(courseId: string, payload: CourseMutationPayload): Promise<Course> {
  return apiRequest<Course>(`/api/v1/courses/${courseId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deleteCourse(courseId: string): Promise<Course> {
  return apiRequest<Course>(`/api/v1/courses/${courseId}`, {
    method: "DELETE",
  });
}
