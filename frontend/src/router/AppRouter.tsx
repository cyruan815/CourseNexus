import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { getSessionToken, subscribeSessionChange } from "../features/auth/session";
import { CourseDetailPage } from "../pages/CourseDetailPage";
import { CourseDetailPreviewPage } from "../pages/CourseDetailPreviewPage";
import { CalendarPage } from "../pages/CalendarPage";
import { GeneratedContentDetailPage } from "../pages/GeneratedContentDetailPage";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";
import { RegisterPage } from "../pages/RegisterPage";
import { StudyPlanCreatePage } from "../pages/StudyPlanCreatePage";
import { StudyPlanDetailPage } from "../pages/StudyPlanDetailPage";
import { WelcomePage } from "../pages/WelcomePage";

function RequireAuth() {
  const [hasSession, setHasSession] = useState(() => Boolean(getSessionToken()));

  useEffect(() => {
    return subscribeSessionChange(() => setHasSession(Boolean(getSessionToken())));
  }, []);

  if (!hasSession) {
    return <Navigate replace to="/welcome" />;
  }

  return <Outlet />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        {import.meta.env.DEV ? <Route element={<CourseDetailPreviewPage />} path="/preview/course-detail" /> : null}
        <Route element={<WelcomePage />} path="/welcome" />
        <Route element={<LoginPage />} path="/login" />
        <Route element={<RegisterPage />} path="/register" />
        <Route element={<RequireAuth />}>
          <Route element={<HomePage />} path="/" />
          <Route element={<CalendarPage />} path="/calendar" />
          <Route element={<CourseDetailPage />} path="/courses/:courseId" />
          <Route element={<StudyPlanCreatePage />} path="/courses/:courseId/study-plans/new" />
          <Route element={<StudyPlanDetailPage />} path="/courses/:courseId/study-plans/:planId" />
          <Route element={<GeneratedContentDetailPage />} path="/generated-contents/:generatedContentId" />
        </Route>
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </BrowserRouter>
  );
}
