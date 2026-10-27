import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { RefreshCcw, ShieldAlert, ShieldCheck } from "lucide-react";
import { Api } from "../../api/endpoints";
import type { AuditRow, ChainResult } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import DataTable from "../../components/DataTable";
import { useToast } from "../../components/Toast";
import { Button, Card, ErrorBanner, fmtDate, Modal, PageHeader } from "../../components/ui";

export default function Audit() {
  const { config } = useAuth();
  const toast = useToast();
  const [page, setPage] = useState(1);
  const audit = useAsync(() => Api.audit({ page, page_size: 25 }), [page]);
  const [chain, setChain] = useState<ChainResult | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);

  async function run(label: string, fn: () => Promise<void>) {
    setBusy(label);
    try {
      await fn();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  }

  const verify = () => run("verify", async () => setChain(await Api.verifyChain()));
  const tamper = () =>
    run("tamper", async () => {
      const r = await Api.tamper();
      setChain(null);
      toast(`Entry #${r.entry_id} edited directly in the database (hash not updated)`, "info");
      audit.reload();
    });
  const reset = () =>
    run("reset", async () => {
      await Api.resetDemo();
      setConfirmReset(false);
      setChain(null);
      setPage(1);
      audit.reload();
      toast("Demo data reset and re-seeded");
    });

  const columns = useMemo<ColumnDef<AuditRow>[]>(
    () => [
      { header: "#", accessorKey: "id", cell: (c) => <span className={chain?.first_broken_id === c.row.original.id ? "font-bold text-sev-high" : ""}>{c.row.original.id}</span> },
      { header: "Time (UTC)", accessorKey: "ts", cell: (c) => <span className="whitespace-nowrap text-xs">{fmtDate(c.row.original.ts, true)}</span> },
      { header: "Actor", accessorKey: "actor", cell: (c) => <div><div>{c.row.original.actor}</div><div className="text-xs text-slate-500">{c.row.original.actor_role}</div></div> },
      { header: "Action", accessorKey: "action", cell: (c) => <span className="font-mono text-xs font-semibold text-navy">{c.row.original.action}</span> },
      { header: "Entity", id: "entity", accessorFn: (r) => `${r.entity_type} ${r.entity_id}`, cell: (c) => <span className="text-xs">{c.row.original.entity_type} {c.row.original.entity_id.length > 12 ? c.row.original.entity_id.slice(0, 8) + "…" : c.row.original.entity_id}</span> },
      { header: "Hash", accessorKey: "hash", enableSorting: false, cell: (c) => <span className="font-mono text-xs text-slate-600" title={c.row.original.hash}>{c.row.original.hash.slice(0, 10)}</span> },
      { header: "Payload", id: "payload", enableSorting: false, cell: (c) => <code className="block max-w-xs truncate text-xs text-slate-500" title={JSON.stringify(c.row.original.payload)}>{JSON.stringify(c.row.original.payload)}</code> },
    ],
    [chain],
  );

  return (
    <>
      <PageHeader
        title="Audit chain"
        subtitle="Append-only, hash-chained log. Each entry's hash covers the previous hash, so any edit breaks verification."
        actions={
          <>
            <Button onClick={verify} loading={busy === "verify"}>
              <ShieldCheck size={16} /> Verify chain
            </Button>
            {config?.demo_mode && (
              <>
                <Button variant="secondary" onClick={tamper} loading={busy === "tamper"}>
                  <ShieldAlert size={16} /> Tamper entry (demo)
                </Button>
                <Button variant="secondary" onClick={() => setConfirmReset(true)}>
                  <RefreshCcw size={16} /> Reset demo data
                </Button>
              </>
            )}
          </>
        }
      />
      {chain &&
        (chain.intact ? (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-3 font-medium text-teal ring-1 ring-emerald-200" role="status">
            <ShieldCheck size={20} /> Chain intact: {chain.entries_checked} entries verified
          </div>
        ) : (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 px-4 py-3 font-medium text-sev-high ring-1 ring-red-200" role="alert">
            <ShieldAlert size={20} /> Chain broken at entry #{chain.first_broken_id} ({chain.entries_checked} entries checked)
          </div>
        ))}
      <Card>
        <ErrorBanner message={audit.error} onRetry={audit.reload} />
        <DataTable
          data={audit.data?.items || []}
          columns={columns}
          loading={audit.loading}
          server={{ total: audit.data?.total || 0, page, pageSize: 25, onPage: setPage }}
        />
      </Card>
      <Modal
        open={confirmReset}
        title="Reset demo data?"
        onClose={() => setConfirmReset(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmReset(false)}>Cancel</Button>
            <Button variant="danger" loading={busy === "reset"} onClick={reset}>Reset and re-seed</Button>
          </>
        }
      >
        <p className="text-sm">This deletes all uploads, reviews, consents and audit entries and restores the original synthetic seed. Signing keys are kept.</p>
      </Modal>
    </>
  );
}
