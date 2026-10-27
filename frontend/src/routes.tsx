import { Route } from "react-router-dom";
import ProtectedRoute from "./auth/ProtectedRoute";
import Layout from "./components/Layout";
import { Card, PageHeader } from "./components/ui";
import AicteDashboard from "./pages/aicte/Dashboard";
import Colleges from "./pages/aicte/Colleges";
import CollegeDetail from "./pages/aicte/CollegeDetail";
import AicteFlags from "./pages/aicte/Flags";
import Matches from "./pages/aicte/Matches";
import MatchReview from "./pages/aicte/MatchReview";
import Risk from "./pages/aicte/Risk";
import Audit from "./pages/aicte/Audit";
import Reports from "./pages/aicte/Reports";
import Ask from "./pages/aicte/Ask";

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
        <Route path="/aicte" element={<AicteDashboard />} />
        <Route path="/aicte/colleges" element={<Colleges />} />
        <Route path="/aicte/colleges/:id" element={<CollegeDetail />} />
        <Route path="/aicte/flags" element={<AicteFlags />} />
        <Route path="/aicte/matches" element={<Matches />} />
        <Route path="/aicte/matches/:id" element={<MatchReview />} />
        <Route path="/aicte/risk" element={<Risk />} />
        <Route path="/aicte/audit" element={<Audit />} />
        <Route path="/aicte/reports" element={<Reports />} />
        <Route path="/aicte/ask" element={<Ask />} />
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
