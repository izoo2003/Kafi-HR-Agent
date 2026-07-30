import type { ReactNode } from "react";
import "./Table.css";

type Props = {
  headers: string[];
  children: ReactNode;
};

export function Table({ headers, children }: Props) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
