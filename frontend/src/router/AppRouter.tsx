import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { getSessionToken } from "../features/auth/session";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";

function RequireAuth() {
  if (!getSessionToken()) {
    return <Navigate replace to="/login" />;
  }

  return <Outlet />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<LoginPage />} path="/login" />
        <Route element={<RequireAuth />}>
          <Route element={<HomePage />} path="/" />
        </Route>
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </BrowserRouter>
  );
}
