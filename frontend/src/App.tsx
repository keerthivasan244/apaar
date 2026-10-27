import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, ROLE_HOME, useAuth } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";
import Layout from "./components/Layout";
import { ToastProvider } from "./components/Toast";
import { LoadingBlock } from "./components/ui";
import Login from "./pages/Login";
import InstitutionDashboard from "./pages/institution/Dashboard";
import Upload from "./pages/institution/Upload";
import InstitutionStudents from "./pages/institution/Students";
import InstitutionFlags from "./pages/institution/Flags";
import InstitutionCredentials from "./pages/institution/Credentials";
import { routesFor } from "./routes";

const PublicVerify = lazy(() => import("./pages/PublicVerify"));

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? ROLE_HOME[user.role] : "/login"} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Suspense fallback={<div className="p-8"><LoadingBlock /></div>}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/verify" element={<PublicVerify />} />
              <Route element={<ProtectedRoute roles={["institution_admin"]}><Layout /></ProtectedRoute>}>
                <Route path="/institution" element={<InstitutionDashboard />} />
                <Route path="/institution/upload" element={<Upload />} />
                <Route path="/institution/students" element={<InstitutionStudents />} />
                <Route path="/institution/flags" element={<InstitutionFlags />} />
                <Route path="/institution/credentials" element={<InstitutionCredentials />} />
              </Route>
              {routesFor()}
              <Route path="*" element={<Home />} />
            </Routes>
          </Suspense>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
