import { Route } from "react-router-dom";
import ProtectedRoute from "./auth/ProtectedRoute";
import Layout from "./components/Layout";
import { Card, PageHeader } from "./components/ui";

function Placeholder({ title }: { title: string }) {
  return (
    <>
      <PageHeader title={title} />
      <Card>Coming in the next phase.</Card>
    </>
  );
}

/** Routes for the AICTE console, student wallet and verifier portal. */
export function routesFor() {
  return (
    <>
      <Route element={<ProtectedRoute roles={["aicte_officer"]}><Layout /></ProtectedRoute>}>
        <Route path="/aicte/*" element={<Placeholder title="AICTE console" />} />
      </Route>
      <Route element={<ProtectedRoute roles={["student"]}><Layout /></ProtectedRoute>}>
        <Route path="/student" element={<Placeholder title="Student wallet" />} />
      </Route>
      <Route element={<ProtectedRoute roles={["verifier"]}><Layout /></ProtectedRoute>}>
        <Route path="/verifier" element={<Placeholder title="Verifier portal" />} />
      </Route>
    </>
  );
}
