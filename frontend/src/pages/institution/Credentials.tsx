import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink } from "lucide-react";
import { Api } from "../../api/endpoints";
import type { CredentialRow, StudentRow } from "../../api/types";
import { useAsync } from "../../hooks/useAsync";
import DataTable from "../../components/DataTable";
import StudentRoster from "../../components/StudentRoster";
import { useToast } from "../../components/Toast";
import { Button, Card, ErrorBanner, fmtDate, inputClass, Modal, PageHeader, StatusChip } from "../../components/ui";

export default function InstitutionCredentials() {
  const toast = useToast();
  const [page, setPage] = useState(1);
  const creds = useAsync(() => Api.credentials({ page, page_size: 10 }), [page]);
  const [revoking, setRevoking] = useState<CredentialRow | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<number | string | null>(null);

  async function issue(s: StudentRow) {
    setBusy(s.id);
    try {
      await Api.issueCredential(s.id);
      toast(`Credential issued to ${s.name}`);
      creds.reload();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  }

  async function revoke() {
    if (!revoking) return;
    setBusy(revoking.id);
    try {
      await Api.revokeCredential(revoking.id, reason || "Revoked by institution");
      toast("Credential revoked");
      setRevoking(null);
      setReason("");
      creds.reload();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  }

  const columns = useMemo<ColumnDef<CredentialRow>[]>(
    () => [
      { header: "Student", accessorKey: "student_name", cell: (c) => <div><div className="font-medium">{c.row.original.student_name}</div><div className="text-xs text-slate-500">{c.row.original.student_code}</div></div> },
      { header: "Credential ID", accessorKey: "id", cell: (c) => <span className="font-mono text-xs">{c.row.original.id.slice(0, 8)}…</span> },
      { header: "Issued", accessorKey: "issued_at", cell: (c) => fmtDate(c.row.original.issued_at) },
      { header: "Status", accessorKey: "status", cell: (c) => <div><StatusChip status={c.row.original.status} />{c.row.original.reason && <div className="mt-1 text-xs text-slate-500">{c.row.original.reason}</div>}</div> },
      {
        header: "",
        id: "actions",
        enableSorting: false,
        cell: (c) => (
          <div className="flex gap-2">
            <a className="inline-flex items-center gap-1 text-sm text-teal underline" href={`/verify?token=${encodeURIComponent(c.row.original.token)}`} target="_blank" rel="noreferrer">
              Verify <ExternalLink size={12} />
            </a>
            {c.row.original.status === "valid" && (
              <button className="text-sm text-sev-high underline" onClick={() => setRevoking(c.row.original)}>
                Revoke
              </button>
            )}
          </div>
        ),
      },
    ],
    [],
  );

  return (
    <>
      <PageHeader title="Credentials" subtitle="Issue Ed25519-signed enrolment credentials that anyone can verify offline, and revoke them centrally." />
      <Card title="Issued credentials" className="mb-6">
        <ErrorBanner message={creds.error} onRetry={creds.reload} />
        <DataTable
          data={creds.data?.items || []}
          columns={columns}
          loading={creds.loading}
          emptyTitle="No credentials issued yet"
          emptyText="Issue one from the student list below."
          server={{ total: creds.data?.total || 0, page, pageSize: 10, onPage: setPage }}
        />
      </Card>
      <Card title="Issue a credential">
        <StudentRoster
          action={(s) => (
            <Button variant="secondary" className="px-3 py-1" loading={busy === s.id} onClick={() => issue(s)}>
              Issue
            </Button>
          )}
        />
      </Card>
      <Modal
        open={!!revoking}
        title="Revoke credential"
        onClose={() => setRevoking(null)}
        footer={<Button variant="danger" loading={busy === revoking?.id} onClick={revoke}>Revoke</Button>}
      >
        <p className="mb-3 text-sm">
          Revoke the credential of <strong>{revoking?.student_name}</strong>? Its signature stays valid, but anyone checking revocation will see it is revoked.
        </p>
        <input className={inputClass} placeholder="Reason, e.g. Withdrawn from programme" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
    </>
  );
}
