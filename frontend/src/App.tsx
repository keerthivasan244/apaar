import { BrowserRouter, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";

function Home() {
  const [health, setHealth] = useState("checking...");
  useEffect(() => {
    fetch("/api/v1/health")
      .then((r) => r.json())
      .then((d) => setHealth(d.status))
      .catch(() => setHealth("unreachable"));
  }, []);
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-navy">APAAR Verify</h1>
      <p className="mt-2 text-sm">API health: {health}</p>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="*" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}
