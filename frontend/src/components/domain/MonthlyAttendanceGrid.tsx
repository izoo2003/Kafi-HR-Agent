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

type DayStatus = { status: string };

/** Sum day-level statuses across employees (half days also count toward lates). */
export function aggregateAttendanceTotals(
  days: DayStatus[],
  latesPerOff: number = 3,
): MonthlyAttendanceTotals {
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
  totals: MonthlyAttendanceTotals;
};

export function MonthlyAttendanceGrid({ periodStart, periodEnd, totals }: Props) {
  const columns: Array<{
    key: keyof MonthlyAttendanceTotals;
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
      hint: `${totals.latesPerOff} lates = 1 late absent (not in Absents)`,
    },
  ];

  return (
    <div className="monthly-attendance">
      <p className="monthly-attendance__period">
        Period <span className="font-data">{periodStart}</span> →{" "}
        <span className="font-data">{periodEnd}</span>
        {totals.employeeCount != null ? (
          <span className="monthly-attendance__meta">
            · <span className="font-data">{totals.employeeCount}</span> employees
          </span>
        ) : null}
      </p>

      <div className="monthly-attendance__summary-scroll">
        <table className="monthly-attendance__summary-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key} data-status={col.status}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {columns.map((col) => (
                <td key={col.key} data-status={col.status} title={col.hint ?? undefined}>
                  <span className="monthly-attendance__total font-data">
                    {totals[col.key] as number}
                  </span>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <p className="monthly-attendance__footnote">
        Totals across all attendance records in this period. Late absents: every{" "}
        <span className="font-data">{totals.latesPerOff}</span> late check-ins (including half
        days) count as <span className="font-data">1</span> late absent — not added to Absents.
      </p>
    </div>
  );
}
