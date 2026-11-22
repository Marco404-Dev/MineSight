import { number, type TableData } from "@/lib/api";

export function DataTable({ data, label }: { data: TableData; label: string }) {
  return <div role="region" aria-label={label} tabIndex={0} className="max-h-[410px] overflow-auto rounded-lg border border-border">
    <table className="w-full border-collapse text-left text-sm">
      <thead className="sticky top-0 bg-[#192a3e] text-xs text-[#dce8f4]">
        <tr>{data.columns.map((column, i) => <th key={i} scope="col" className="whitespace-nowrap px-3 py-3">{column}</th>)}</tr>
      </thead>
      <tbody className="divide-y divide-border">
        {data.rows.map((row, i) => <tr key={i} className="hover:bg-[#1b2c41]">
          {row.map((value, j) => <td key={j} className="max-w-64 truncate px-3 py-2.5 tabular-nums" title={String(value ?? "")}>
            {typeof value === "number" ? number(value) : String(value ?? "—")}
          </td>)}
        </tr>)}
      </tbody>
    </table>
  </div>;
}
