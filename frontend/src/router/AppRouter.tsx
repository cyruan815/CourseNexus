import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { getSessionToken } from "../features/auth/session";
import { CourseDetailPage } from "../pages/CourseDetailPage";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";
import { RegisterPage } from "../pages/RegisterPage";
import { WelcomePage } from "../pages/WelcomePage";

function RequireAuth() {
  if (!getSessionToken()) {
    return <Navigate replace to="/welcome" />;
  }

  return <Outlet />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<WelcomePage />} path="/welcome" />
        <Route element={<LoginPage />} path="/login" />
        <Route element={<RegisterPage />} path="/register" />
        <Route element={<RequireAuth />}>
          <Route element={<HomePage />} path="/" />
          <Route element={<CourseDetailPage />} path="/courses/:courseId" />
        </Route>
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </BrowserRouter>
  );
}
