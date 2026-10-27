import { createContext, ReactNode, useCallback, useContext, useState } from "react";
import { CheckCircle2, AlertTriangle, X } from "lucide-react";

type Kind = "success" | "error" | "info";
interface ToastItem {
  id: number;
  kind: Kind;
  text: string;
}

const ToastContext = createContext<(text: string, kind?: Kind) => void>(() => {});
let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const dismiss = (id: number) => setItems((all) => all.filter((t) => t.id !== id));
  const push = useCallback((text: string, kind: Kind = "success") => {
    const id = nextId++;
    setItems((all) => [...all, { id, kind, text }]);
    setTimeout(() => dismiss(id), 4500);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2" role="status" aria-live="polite">
        {items.map((t) => (
          <div
            key={t.id}
            className={`flex items-start gap-2 rounded-lg px-4 py-3 text-sm text-white shadow-lg ${
              t.kind === "error" ? "bg-sev-high" : t.kind === "info" ? "bg-navy" : "bg-teal"
            }`}
          >
            {t.kind === "error" ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
            <span className="flex-1">{t.text}</span>
            <button onClick={() => dismiss(t.id)} aria-label="Dismiss">
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
