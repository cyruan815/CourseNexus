import { apiRequest } from "../../api/client";
import type { Course } from "../../types/course";

export interface CourseMutationPayload {
  name?: string;
  description?: string | null;
  teacher?: string | null;
  term?: string | null;
}

export function listCourses(): Promise<Course[]> {
  return apiRequest<Course[]>("/api/v1/courses");
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
