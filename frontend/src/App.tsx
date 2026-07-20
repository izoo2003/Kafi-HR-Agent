import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { PositionDetail } from "./pages/PositionDetail";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/positions/:position" element={<PositionDetail />} />
      </Routes>
    </Layout>
  );
}
