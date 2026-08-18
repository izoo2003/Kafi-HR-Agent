import { useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { StatusBadge } from "../../components/ui/Badge";
import { Table } from "../../components/ui/Table";
import { Pagination } from "../../components/ui/Pagination";
import {
  useAttendanceRecords,
  useAttendanceRules,
  useCreateAttendance,
  useImportAttendance,
} from "../../hooks/useAttendance";
import { useEmployees } from "../../hooks/useEmployees";
import { usePagination } from "../../hooks/usePagination";
import { syncBiometric, attendanceImportTemplateCsv } from "../../api/attendance";
import { ATTENDANCE_STATUS_LABELS } from "../../constants/statusLabels";
import { ApiError } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import { isSelfService } from "../../lib/selfService";

export function AttendanceRecordsPage() {
  const { user, hasPermission } = useAuth();
  const selfService = isSelfService(user);
  const canWrite = hasPermission("attendance", "write");
  const { page, pageSize, setPage, params } = usePagination(1, 50);
  const records = useAttendanceRecords(params);
  const employees = useEmployees({
    page: 1,
    pageSize: 100,
    status: "active",
    enabled: canWrite && !selfService,
  });
  const rules = useAttendanceRules();
  const create = useCreateAttendance();
  const importMut = useImportAttendance();
  const fileRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({
    employeeId: "",
    date: new Date().toISOString().slice(0, 10),
    checkIn: "09:00",
    checkOut: "18:00",
  });
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<string | null>(null);
  const [bioMsg, setBioMsg] = useState<string | null>(null);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const date = form.date;
      await create.mutateAsync({
        employeeId: Number(form.employeeId),
        date,
        checkIn: `${date}T${form.checkIn}:00+05:00`,
        checkOut: `${date}T${form.checkOut}:00+05:00`,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create record");
    }
  }

  async function onImport(files: FileList | null) {
    if (!files?.[0]) return;
    setImportResult(null);
    setError(null);
    try {
      const res = await importMut.mutateAsync(files[0]);
      const errText = res.errors.map((e) => `Row ${e.row}: ${e.message}`).join("; ");
      setImportResult(`Imported ${res.imported}.${errText ? ` Errors — ${errText}` : ""}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed");
    }
  }

  return (
    <>
      <PageHeader
        title={selfService ? "My attendance records" : "Attendance Records"}
        breadcrumb="Attendance / Records"
        actions={
          <Link to="/attendance">
            <Button variant="secondary">Overview</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {importResult ? <p style={{ color: "var(--color-text-secondary)" }}>{importResult}</p> : null}
        {bioMsg ? <p style={{ color: "var(--color-status-warning)" }}>{bioMsg}</p> : null}

        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Shift rules</h2>
          {(rules.data ?? []).map((r) => (
            <p key={r.id} style={{ margin: 0 }}>
              <strong>{r.name}</strong> — {r.shiftStart}–{r.shiftEnd}, grace{" "}
              <span className="font-data">{r.gracePeriodMinutes}</span> min, half-day threshold{" "}
              <span className="font-data">{r.halfDayThresholdMinutes}</span> min
              {r.appliesToDepartmentId ? ` (dept ${r.appliesToDepartmentId})` : " (company-wide)"}
            </p>
          ))}
        </section>

        {canWrite ? (
          <>
        <section className="card">
          <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Manual entry</h2>
          <form
            onSubmit={onCreate}
            style={{
              display: "grid",
              gap: "var(--space-3)",
              gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
            }}
          >
            <label className="form-field">
              <span className="form-field__label">Employee</span>
              <select
                className="form-field__input"
                value={form.employeeId}
                onChange={(e) => setForm({ ...form, employeeId: e.target.value })}
                required
              >
                <option value="">Select…</option>
                {(employees.data?.items ?? []).map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.fullName} ({e.employeeCode})
                  </option>
                ))}
              </select>
            </label>
            <FormField
              label="Date"
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              required
            />
            <FormField
              label="Check in"
              type="time"
              value={form.checkIn}
              onChange={(e) => setForm({ ...form, checkIn: e.target.value })}
            />
            <FormField
              label="Check out"
              type="time"
              value={form.checkOut}
              onChange={(e) => setForm({ ...form, checkOut: e.target.value })}
            />
            <div style={{ alignSelf: "end" }}>
              <Button type="submit" variant="primary">
                Add Attendance Record
              </Button>
            </div>
          </form>
        </section>

        <section className="card" style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
          <Link to="/attendance/period-report">
            <Button variant="primary">Excel period report</Button>
          </Link>
          <Button variant="secondary" onClick={() => fileRef.current?.click()}>
            Import CSV/Excel
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            hidden
            onChange={(e) => onImport(e.target.files)}
          />
          <Button
            variant="secondary"
            onClick={() => {
              const blob = new Blob([attendanceImportTemplateCsv()], { type: "text/csv" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = "attendance_import_template.csv";
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            Download Template
          </Button>
          <Button
            variant="secondary"
            onClick={async () => {
              const res = await syncBiometric();
              setBioMsg(res.message);
            }}
          >
            Sync Biometric Device
          </Button>
        </section>
          </>
        ) : null}

        {records.isLoading ? <Spinner label="Loading records" /> : null}
        {records.data && records.data.items.length === 0 ? (
          <EmptyState
            title="No attendance records"
            description="Add a manual record or import a device export CSV (employee_code, date, check_in, check_out)."
          />
        ) : null}
        {records.data && records.data.items.length > 0 ? (
          <>
            <Table headers={["Date", "Employee", "In", "Out", "Status", "Source"]}>
              {records.data.items.map((r) => (
                <tr key={r.id} data-status={r.status}>
                  <td className="num">{r.date}</td>
                  <td className="num">{r.employeeId}</td>
                  <td className="num">{r.checkIn ? new Date(r.checkIn).toLocaleTimeString() : "—"}</td>
                  <td className="num">{r.checkOut ? new Date(r.checkOut).toLocaleTimeString() : "—"}</td>
                  <td>
                    <StatusBadge status={r.status}>
                      {ATTENDANCE_STATUS_LABELS[r.status as keyof typeof ATTENDANCE_STATUS_LABELS] ??
                        r.status}
                    </StatusBadge>
                  </td>
                  <td>{r.source}</td>
                </tr>
              ))}
            </Table>
            <Pagination
              page={page}
              pageSize={pageSize}
              total={records.data.total}
              onPageChange={setPage}
            />
          </>
        ) : null}
      </div>
    </>
  );
}
