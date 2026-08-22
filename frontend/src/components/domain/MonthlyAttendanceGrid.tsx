import "./MonthlyAttendanceGrid.css";

export type MonthlyAttendanceTotals = {
  daysPresent: number;
  daysAbsent: number;
  daysLate: number;
  daysHalfDay: number;
  daysOff: number;
  lateAbsents: number;
  latesPerOff: number;
  employeeCount?: number;
};

export type MonthlyAttendanceEmployeeRow = {
  employeeId: number;
  fullName: string;
  employeeCode: string;
  daysPresent: number;
  daysAbsent: number;
  daysLate: number;
  daysHalfDay: number;
  daysOff: number;
  lateAbsents: number;
};

type DayStatus = { status: string };

/** Sum day-level statuses for one employee (half days also count toward lates). */
export function aggregateAttendanceTotals(
  days: DayStatus[],
  latesPerOff: number = 3,
): Omit<MonthlyAttendanceTotals, "employeeCount"> {
  let daysPresent = 0;
  let daysAbsent = 0;
  let daysLate = 0;
  let daysHalfDay = 0;
  let daysOff = 0;

  for (const day of days) {
    switch (day.status) {
      case "present":
        daysPresent += 1;
        break;
      case "absent":
        daysAbsent += 1;
        break;
      case "late":
        daysLate += 1;
        break;
      case "half_day":
        daysHalfDay += 1;
        daysLate += 1;
        break;
      case "holiday":
        daysOff += 1;
        break;
      default:
        break;
    }
  }

  return {
    daysPresent,
    daysAbsent,
    daysLate,
    daysHalfDay,
    daysOff,
    lateAbsents: Math.floor(daysLate / Math.max(1, latesPerOff)),
    latesPerOff,
  };
}

type Props = {
  periodStart: string;
  periodEnd: string;
  employees: MonthlyAttendanceEmployeeRow[];
  latesPerOff: number;
};

export function MonthlyAttendanceGrid({ periodStart, periodEnd, employees, latesPerOff }: Props) {
  const columns: Array<{
    key: keyof Omit<MonthlyAttendanceEmployeeRow, "employeeId" | "fullName" | "employeeCode">;
    label: string;
    status?: string;
    hint?: string;
  }> = [
    { key: "daysPresent", label: "Presents", status: "positive" },
    { key: "daysAbsent", label: "Absents", status: "critical", hint: "Actual absents only" },
    { key: "daysLate", label: "Lates", status: "warning" },
    { key: "daysHalfDay", label: "Half days", status: "warning" },
    { key: "daysOff", label: "Off", status: "neutral", hint: "Holidays / company off" },
    {
      key: "lateAbsents",
      label: "Late absents",
      status: "critical",
      hint: `${latesPerOff} lates = 1 late absent (not in Absents)`,
    },
  ];

  return (
    <div className="monthly-attendance">
      <p className="monthly-attendance__period">
        Period <span className="font-data">{periodStart}</span> →{" "}
        <span className="font-data">{periodEnd}</span>
        <span className="monthly-attendance__meta">
          · <span className="font-data">{employees.length}</span> employees
        </span>
      </p>

      <div className="monthly-attendance__summary-scroll">
        <table className="monthly-attendance__summary-table">
          <thead>
            <tr>
              <th className="monthly-attendance__employee-col">Employee</th>
              {columns.map((col) => (
                <th key={col.key} data-status={col.status}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {employees.length === 0 ? (
              <tr>
                <td colSpan={columns.length + 1} className="monthly-attendance__empty">
                  No employees in this view.
                </td>
              </tr>
            ) : (
              employees.map((emp) => (
                <tr key={emp.employeeId} className="monthly-attendance__row">
                  <td className="monthly-attendance__employee-col">
                    <span className="monthly-attendance__name">{emp.fullName}</span>
                    {emp.employeeCode ? (
                      <span className="monthly-attendance__code font-data">{emp.employeeCode}</span>
                    ) : null}
                  </td>
                  {columns.map((col) => (
                    <td key={col.key} data-status={col.status} title={col.hint ?? undefined}>
                      <span className="monthly-attendance__total font-data">
                        {emp[col.key] as number}
                      </span>
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="monthly-attendance__footnote">
        Per-employee totals for attendance records in this period. Late absents: every{" "}
        <span className="font-data">{latesPerOff}</span> late check-ins (including half days) count
        as <span className="font-data">1</span> late absent — not added to Absents.
      </p>
    </div>
  );
}
