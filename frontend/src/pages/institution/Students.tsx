import StudentRoster from "../../components/StudentRoster";
import { Button, Card, PageHeader } from "../../components/ui";
import { download } from "../../api/client";
import { Download } from "lucide-react";

export default function InstitutionStudents() {
  return (
    <>
      <PageHeader
        title="Students"
        subtitle="Your institution's roster for the current academic year. APAAR IDs are masked."
        actions={
          <Button variant="secondary" onClick={() => download("/reports/roster?format=csv", "roster.csv")}>
            <Download size={16} /> Export roster
          </Button>
        }
      />
      <Card>
        <StudentRoster />
      </Card>
    </>
  );
}
