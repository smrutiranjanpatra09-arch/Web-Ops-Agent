import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import TaskIntake from "./pages/TaskIntake";
import Runs from "./pages/Runs";
import RunDetail from "./pages/RunDetail";
import Reviews from "./pages/Reviews";
import Signals from "./pages/Signals";
import Assistant from "./pages/Assistant";
import Dashboard from "./pages/Dashboard";
import SourceHealth from "./pages/SourceHealth";
import Schedules from "./pages/Schedules";
import Failures from "./pages/Failures";
import SystemHealth from "./pages/SystemHealth";
import AiActivity from "./pages/AiActivity";
import DataManagement from "./pages/DataManagement";
import PlanReviewQueue from "./pages/journey/PlanReviewQueue";
import BrowserMonitorQueue from "./pages/journey/BrowserMonitorQueue";
import ExtractedDataQueue from "./pages/journey/ExtractedDataQueue";
import ComparisonFeed from "./pages/journey/ComparisonFeed";
import CompletionQueue from "./pages/journey/CompletionQueue";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/tasks/new" replace />} />
          <Route path="/tasks/new" element={<TaskIntake />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/runs/history" element={<Runs />} />
          <Route path="/runs/:runId" element={<RunDetail />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/assistant" element={<Assistant />} />
          <Route path="/sources" element={<SourceHealth />} />
          <Route path="/schedules" element={<Schedules />} />
          <Route path="/failures" element={<Failures />} />
          <Route path="/system" element={<SystemHealth />} />
          <Route path="/data-management" element={<DataManagement />} />
          <Route path="/ai-activity" element={<AiActivity />} />
          <Route path="/journey/plan" element={<PlanReviewQueue />} />
          <Route path="/journey/browse" element={<BrowserMonitorQueue />} />
          <Route path="/journey/data" element={<ExtractedDataQueue />} />
          <Route path="/journey/compare" element={<ComparisonFeed />} />
          <Route path="/journey/complete" element={<CompletionQueue />} />
        </Route>
      </Route>
    </Routes>
  );
}
