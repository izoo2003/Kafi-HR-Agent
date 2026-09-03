import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { FormField } from "../../components/ui/FormField";
import { Spinner } from "../../components/ui/Spinner";
import { Table } from "../../components/ui/Table";
import {
  useCreateTaxYear,
  useReplaceTaxSlabs,
  useTaxYears,
  useUpdateTaxYear,
} from "../../hooks/usePayroll";
import { useLocalDraftPersist } from "../../hooks/useLocalDraftPersist";
import { useAuth } from "../../hooks/useAuth";
import { ApiError } from "../../api/client";
import { clearLocalDraft, formatDraftRestoredMessage, loadLocalDraft } from "../../lib/localDraft";
import type { TaxSlabInput } from "../../types/payroll";

function emptySlab(order: number): TaxSlabInput {
  return {
    sortOrder: order,
    minAmount: 0,
    maxAmount: null,
    fixedAmount: 0,
    ratePercent: 0,
    excessOver: 0,
  };
}

function money(n: string | number | null | undefined): string {
  if (n == null || n === "") return "—";
  return Number(n).toLocaleString("en-PK");
}

export function TaxSlabsPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("payroll", "write");
  const years = useTaxYears();
  const createYear = useCreateTaxYear();
  const updateYear = useUpdateTaxYear();
  const replaceSlabs = useReplaceTaxSlabs();

  const [selectedId, setSelectedId] = useState<number | "">("");
  const [slabs, setSlabs] = useState<TaxSlabInput[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [newLabel, setNewLabel] = useState("");
  const [newStart, setNewStart] = useState("");
  const [newEnd, setNewEnd] = useState("");
  const [draftMessage, setDraftMessage] = useState<string | null>(null);
  const restoredRef = useRef(false);
  const keepRestoredSlabsRef = useRef(false);

  const selected = useMemo(
    () => (years.data ?? []).find((y) => y.id === selectedId) ?? null,
    [years.data, selectedId],
  );

  useEffect(() => {
    if (!years.data?.length) return;
    if (selectedId === "") {
      const active = years.data.find((y) => y.isActive) ?? years.data[0];
      setSelectedId(active.id);
    }
  }, [years.data, selectedId]);

  useEffect(() => {
    if (keepRestoredSlabsRef.current) {
      keepRestoredSlabsRef.current = false;
      return;
    }
    if (!selected) {
      setSlabs([]);
      return;
    }
    setSlabs(
      selected.slabs.map((s) => ({
        sortOrder: s.sortOrder,
        minAmount: Number(s.minAmount),
        maxAmount: s.maxAmount == null ? null : Number(s.maxAmount),
        fixedAmount: Number(s.fixedAmount),
        ratePercent: Number(s.ratePercent),
        excessOver: Number(s.excessOver),
      })),
    );
  }, [selected]);

  const draftScope = "tax_slabs_page";
  const draftDirty =
    selectedId !== "" ||
    slabs.length > 0 ||
    Boolean(newLabel.trim() || newStart || newEnd);
  useLocalDraftPersist({
    scope: draftScope,
    dirty: draftDirty,
    enabled: canWrite,
    data: { selectedId, slabs, newLabel, newStart, newEnd },
    isEmpty: (d) =>
      d.selectedId === "" &&
      d.slabs.length === 0 &&
      !d.newLabel.trim() &&
      !d.newStart &&
      !d.newEnd,
  });

  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    const draft = loadLocalDraft<{
      selectedId: number | "";
      slabs: TaxSlabInput[];
      newLabel: string;
      newStart: string;
      newEnd: string;
    }>(draftScope);
    if (!draft?.data) return;
    keepRestoredSlabsRef.current = true;
    setSelectedId(draft.data.selectedId ?? "");
    setSlabs(draft.data.slabs ?? []);
    setNewLabel(draft.data.newLabel ?? "");
    setNewStart(draft.data.newStart ?? "");
    setNewEnd(draft.data.newEnd ?? "");
    setDraftMessage(formatDraftRestoredMessage(draft.savedAt, "tax slab draft"));
  }, []);

  function updateSlab(idx: number, patch: Partial<TaxSlabInput>) {
    setSlabs((prev) => prev.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  }

  async function onSaveSlabs() {
    if (!selected) return;
    setError(null);
    setMessage(null);
    setDraftMessage(null);
    try {
      await replaceSlabs.mutateAsync({
        id: selected.id,
        slabs: slabs.map((s, i) => ({ ...s, sortOrder: i + 1 })),
      });
      clearLocalDraft(draftScope);
      setMessage("Tax slabs saved");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save slabs");
    }
  }

  async function onCreateYear(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setDraftMessage(null);
    try {
      const created = await createYear.mutateAsync({
        label: newLabel.trim(),
        startDate: newStart,
        endDate: newEnd,
        isActive: true,
        slabs: slabs.length
          ? slabs
          : [
              emptySlab(1),
              { ...emptySlab(2), minAmount: 600001, maxAmount: 1200000, ratePercent: 1, excessOver: 600000 },
            ],
      });
      setSelectedId(created.id);
      setNewLabel("");
      setNewStart("");
      setNewEnd("");
      clearLocalDraft(draftScope);
      setMessage(`Tax year ${created.label} created`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create tax year");
    }
  }

  async function toggleActive() {
    if (!selected) return;
    try {
      await updateYear.mutateAsync({
        id: selected.id,
        payload: { isActive: !selected.isActive },
      });
      setMessage(selected.isActive ? "Marked inactive" : "Marked active");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    }
  }

  return (
    <>
      <PageHeader
        title="Tax slabs"
        breadcrumb="Payroll / Tax slabs"
        actions={
          <Link to="/payroll/runs">
            <Button variant="secondary">Back to payroll</Button>
          </Link>
        }
      />
      <div className="page" style={{ display: "grid", gap: "var(--space-5)" }}>
        {error ? <p style={{ color: "var(--color-status-critical)", margin: 0 }}>{error}</p> : null}
        {message ? <p style={{ color: "var(--color-status-positive)", margin: 0 }}>{message}</p> : null}
        {draftMessage ? <p style={{ color: "var(--color-status-warning)", margin: 0 }}>{draftMessage}</p> : null}

        <Card>
          <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Tax year</h2>
          <p style={{ marginTop: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
            Select a tax year (e.g. 2026-27) to view or edit progressive annual salary tax slabs.
            Slabs apply to annualized <strong>net</strong> (gross minus late, half-day, loan, and
            advance deductions) — not gross. Monthly withholding = annual tax ÷ 12.
          </p>
          {years.isLoading ? <Spinner /> : null}
          <label className="form-field" style={{ maxWidth: 320 }}>
            <span className="form-field__label">Tax year</span>
            <select
              className="form-field__input"
              value={selectedId === "" ? "" : String(selectedId)}
              onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Select…</option>
              {(years.data ?? []).map((y) => (
                <option key={y.id} value={y.id}>
                  {y.label}
                  {y.isActive ? " (active)" : ""}
                </option>
              ))}
            </select>
          </label>
          {selected ? (
            <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
              {selected.startDate} → {selected.endDate}
              {selected.notes ? ` · ${selected.notes}` : ""}
              {canWrite ? (
                <>
                  {" · "}
                  <Button type="button" variant="secondary" onClick={toggleActive}>
                    {selected.isActive ? "Deactivate" : "Activate"}
                  </Button>
                </>
              ) : null}
            </p>
          ) : null}
        </Card>

        {canWrite ? (
          <Card>
            <h2 style={{ marginTop: 0, fontSize: "var(--text-lg)" }}>Add tax year</h2>
            <form
              onSubmit={onCreateYear}
              style={{
                display: "grid",
                gap: "var(--space-3)",
                gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
              }}
            >
              <FormField
                label="Label"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                placeholder="2027-28"
                required
              />
              <FormField
                label="Start date"
                type="date"
                value={newStart}
                onChange={(e) => setNewStart(e.target.value)}
                required
              />
              <FormField
                label="End date"
                type="date"
                value={newEnd}
                onChange={(e) => setNewEnd(e.target.value)}
                required
              />
              <div style={{ alignSelf: "end" }}>
                <Button type="submit" variant="secondary" disabled={createYear.isPending}>
                  Create tax year
                </Button>
              </div>
            </form>
          </Card>
        ) : null}

        {selected ? (
          <Card>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "var(--space-3)",
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>
                Slabs for {selected.label}
              </h2>
              {canWrite ? (
                <div style={{ display: "flex", gap: "var(--space-2)" }}>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setSlabs([...slabs, emptySlab(slabs.length + 1)])}
                  >
                    Add slab
                  </Button>
                  <Button
                    type="button"
                    variant="primary"
                    disabled={replaceSlabs.isPending || slabs.length === 0}
                    onClick={onSaveSlabs}
                  >
                    {replaceSlabs.isPending ? "Saving…" : "Save slabs"}
                  </Button>
                </div>
              ) : null}
            </div>

            <Table
              headers={[
                "Order",
                "Min (annual)",
                "Max (annual)",
                "Fixed tax",
                "Rate %",
                "Excess over",
                ...(canWrite ? ["Actions"] : []),
              ]}
            >
              {slabs.map((s, idx) => (
                <tr key={idx} data-status="info">
                  <td className="num">{idx + 1}</td>
                  <td>
                    {canWrite ? (
                      <input
                        className="form-field__input font-data"
                        type="number"
                        value={s.minAmount}
                        onChange={(e) => updateSlab(idx, { minAmount: Number(e.target.value) })}
                        style={{ width: 120 }}
                      />
                    ) : (
                      <span className="num">{money(s.minAmount)}</span>
                    )}
                  </td>
                  <td>
                    {canWrite ? (
                      <input
                        className="form-field__input font-data"
                        type="number"
                        placeholder="∞"
                        value={s.maxAmount ?? ""}
                        onChange={(e) =>
                          updateSlab(idx, {
                            maxAmount: e.target.value === "" ? null : Number(e.target.value),
                          })
                        }
                        style={{ width: 120 }}
                      />
                    ) : (
                      <span className="num">{s.maxAmount == null ? "∞" : money(s.maxAmount)}</span>
                    )}
                  </td>
                  <td>
                    {canWrite ? (
                      <input
                        className="form-field__input font-data"
                        type="number"
                        value={s.fixedAmount}
                        onChange={(e) => updateSlab(idx, { fixedAmount: Number(e.target.value) })}
                        style={{ width: 110 }}
                      />
                    ) : (
                      <span className="num">{money(s.fixedAmount)}</span>
                    )}
                  </td>
                  <td>
                    {canWrite ? (
                      <input
                        className="form-field__input font-data"
                        type="number"
                        step="0.01"
                        value={s.ratePercent}
                        onChange={(e) => updateSlab(idx, { ratePercent: Number(e.target.value) })}
                        style={{ width: 80 }}
                      />
                    ) : (
                      <span className="num">{s.ratePercent}</span>
                    )}
                  </td>
                  <td>
                    {canWrite ? (
                      <input
                        className="form-field__input font-data"
                        type="number"
                        value={s.excessOver}
                        onChange={(e) => updateSlab(idx, { excessOver: Number(e.target.value) })}
                        style={{ width: 120 }}
                      />
                    ) : (
                      <span className="num">{money(s.excessOver)}</span>
                    )}
                  </td>
                  {canWrite ? (
                    <td>
                      <Button
                        type="button"
                        variant="destructive"
                        disabled={slabs.length <= 1}
                        onClick={() => setSlabs(slabs.filter((_, i) => i !== idx))}
                      >
                        Remove
                      </Button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </Table>
          </Card>
        ) : null}
      </div>
    </>
  );
}
