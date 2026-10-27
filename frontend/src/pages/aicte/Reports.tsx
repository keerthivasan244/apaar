import { useState } from "react";
import { Download } from "lucide-react";
import { download } from "../../api/client";
import { Api } from "../../api/endpoints";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../components/Toast";
import { Button, Card, PageHeader, Select } from "../../components/ui";

export default function Reports() {
  const toast = useToast();
  const colleges = useAsync(() => Api.colleges(), []);
  const [collegeId, setCollegeId] = useState("1");
  const get = (path: string, name: string) => download(path, name).catch((e: Error) => toast(e.message, "error"));
  return (
    <>
      <PageHeader title="Reports" subtitle="Downloads for inspections. Exported text is protected against spreadsheet formula injection." />
      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Compliance summary">
          <p className="mb-4 text-sm text-slate-600">Per institution: approved intake, admitted, excess, open flags, suspected duplicates, risk score and band.</p>
          <div className="flex gap-2">
            <Button onClick={() => get("/reports/compliance?format=csv", "compliance.csv")}><Download size={16} /> CSV</Button>
            <Button variant="secondary" onClick={() => get("/reports/compliance?format=xlsx", "compliance.xlsx")}><Download size={16} /> XLSX</Button>
          </div>
        </Card>
        <Card title="Institution roster">
          <p className="mb-3 text-sm text-slate-600">All current-year records of one institution with open flag counts.</p>
          <div className="mb-4">
            <Select label="Institution" value={collegeId} onChange={setCollegeId} options={(colleges.data || []).map((c) => ({ value: String(c.id), label: `${c.aicte_id} ${c.name}` }))} />
          </div>
          <div className="flex gap-2">
            <Button onClick={() => get(`/reports/roster?college_id=${collegeId}&format=csv`, `roster_${collegeId}.csv`)}><Download size={16} /> CSV</Button>
            <Button variant="secondary" onClick={() => get(`/reports/roster?college_id=${collegeId}&format=xlsx`, `roster_${collegeId}.xlsx`)}><Download size={16} /> XLSX</Button>
          </div>
        </Card>
      </div>
      <p className="mt-6 text-xs text-slate-500">Policy values illustrative; check against the current AICTE Approval Process Handbook before quoting.</p>
    </>
  );
}
