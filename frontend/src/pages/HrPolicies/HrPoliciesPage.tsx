import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  CalendarOff,
  Check,
  ClipboardList,
  Copy,
  FileText,
  Lock,
  Pencil,
  Plus,
  Timer,
  Trash2,
  X,
} from "lucide-react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { ApiError } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import { useHrPolicies, useSaveHrPolicies } from "../../hooks/useHrPolicies";
import type {
  HrPoliciesDocument,
  HrPolicyIcon,
  HrPolicyItem,
  HrPolicySection,
} from "../../types/hrPolicies";
import "./HrPoliciesPage.css";

const ICONS: Record<HrPolicyIcon, ReactNode> = {
  documents: <FileText size={18} strokeWidth={1.75} aria-hidden />,
  timings: <Timer size={18} strokeWidth={1.75} aria-hidden />,
  sop: <ClipboardList size={18} strokeWidth={1.75} aria-hidden />,
  leave: <CalendarOff size={18} strokeWidth={1.75} aria-hidden />,
  confidentiality: <Lock size={18} strokeWidth={1.75} aria-hidden />,
};

function cloneDoc(doc: HrPoliciesDocument): HrPoliciesDocument {
  return {
    welcomeTitle: doc.welcomeTitle,
    welcomeSubtitle: doc.welcomeSubtitle,
    sections: doc.sections.map((s) => ({
      ...s,
      items: s.items.map((it) => ({
        text: it.text,
        quoted: it.quoted,
        children: [...(it.children ?? [])],
      })),
    })),
  };
}

function emptyItem(): HrPolicyItem {
  return { text: "", quoted: false, children: [] };
}

function PolicyItems({ section }: { section: HrPolicySection }) {
  const Tag = section.listStyle === "ol" ? "ol" : "ul";
  if (section.listStyle === "paragraphs") {
    return (
      <div className={section.icon === "confidentiality" ? undefined : "hr-policies__sop"}>
        {section.items.map((item, i) =>
          item.quoted ? (
            <p key={`${section.id}-${i}`} className="hr-policies__quote">
              “{item.text}”
            </p>
          ) : (
            <p key={`${section.id}-${i}`}>{item.text}</p>
          ),
        )}
      </div>
    );
  }
  return (
    <Tag>
      {section.items.map((item, i) => (
        <li key={`${section.id}-${i}`}>
          {item.quoted ? <p className="hr-policies__quote">“{item.text}”</p> : item.text}
          {item.children?.length ? (
            <ul className="hr-policies__nested">
              {item.children.map((child, ci) => (
                <li key={ci}>{child}</li>
              ))}
            </ul>
          ) : null}
        </li>
      ))}
    </Tag>
  );
}

export function HrPoliciesPage() {
  const { hasPermission } = useAuth();
  const canEdit = hasPermission("employees", "write");
  const query = useHrPolicies();
  const saveMut = useSaveHrPolicies();
  const bodyRef = useRef<HTMLElement>(null);
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<HrPoliciesDocument | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editing && query.data) {
      setDraft(cloneDoc(query.data));
    }
  }, [query.data, editing]);

  async function copyAll() {
    const text = bodyRef.current?.innerText.replace(/\n{3,}/g, "\n\n").trim() ?? "";
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      document.body.removeChild(area);
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  function startEdit() {
    if (!query.data) return;
    setError(null);
    setDraft(cloneDoc(query.data));
    setEditing(true);
  }

  function cancelEdit() {
    setError(null);
    setEditing(false);
    if (query.data) setDraft(cloneDoc(query.data));
  }

  async function save() {
    if (!draft) return;
    setError(null);
    const payload: HrPoliciesDocument = {
      welcomeTitle: draft.welcomeTitle.trim(),
      welcomeSubtitle: draft.welcomeSubtitle.trim(),
      sections: draft.sections.map((s) => ({
        ...s,
        title: s.title.trim(),
        items: s.items
          .map((it) => ({
            ...it,
            text: it.text.trim(),
            children: (it.children ?? []).map((c) => c.trim()).filter(Boolean),
          }))
          .filter((it) => it.text.length > 0),
      })),
    };
    if (!payload.welcomeTitle) {
      setError("Add a heading before saving.");
      return;
    }
    if (payload.sections.some((s) => !s.title || s.items.length === 0)) {
      setError("Each section needs a title and at least one point.");
      return;
    }
    try {
      await saveMut.mutateAsync(payload);
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save HR policies");
    }
  }

  function patchWelcome(patch: Partial<Pick<HrPoliciesDocument, "welcomeTitle" | "welcomeSubtitle">>) {
    setDraft((prev) => (prev ? { ...prev, ...patch } : prev));
  }

  function patchSection(index: number, patch: Partial<HrPolicySection>) {
    setDraft((prev) => {
      if (!prev) return prev;
      const sections = prev.sections.map((s, i) => (i === index ? { ...s, ...patch } : s));
      return { ...prev, sections };
    });
  }

  function patchItem(sectionIndex: number, itemIndex: number, patch: Partial<HrPolicyItem>) {
    setDraft((prev) => {
      if (!prev) return prev;
      const sections = prev.sections.map((s, i) => {
        if (i !== sectionIndex) return s;
        return {
          ...s,
          items: s.items.map((it, j) => (j === itemIndex ? { ...it, ...patch } : it)),
        };
      });
      return { ...prev, sections };
    });
  }

  function addItem(sectionIndex: number) {
    setDraft((prev) => {
      if (!prev) return prev;
      const sections = prev.sections.map((s, i) =>
        i === sectionIndex ? { ...s, items: [...s.items, emptyItem()] } : s,
      );
      return { ...prev, sections };
    });
  }

  function removeItem(sectionIndex: number, itemIndex: number) {
    setDraft((prev) => {
      if (!prev) return prev;
      const sections = prev.sections.map((s, i) => {
        if (i !== sectionIndex || s.items.length <= 1) return s;
        return { ...s, items: s.items.filter((_, j) => j !== itemIndex) };
      });
      return { ...prev, sections };
    });
  }

  const doc = editing ? draft : query.data;
  const confidentialClass = (icon: HrPolicyIcon) =>
    icon === "confidentiality" ? " hr-policies__confidential" : "";

  return (
    <>
      <PageHeader
        title="HR Policies"
        breadcrumb="HR Policies"
        actions={
          <>
            {editing ? (
              <>
                <Button variant="secondary" onClick={cancelEdit} disabled={saveMut.isPending}>
                  <X size={16} aria-hidden />
                  Cancel
                </Button>
                <Button variant="primary" onClick={() => void save()} disabled={saveMut.isPending || !draft}>
                  {saveMut.isPending ? "Saving…" : "Save policies"}
                </Button>
              </>
            ) : (
              <>
                {canEdit ? (
                  <Button variant="primary" onClick={startEdit} disabled={!query.data}>
                    <Pencil size={16} aria-hidden />
                    Edit
                  </Button>
                ) : null}
                <Button variant="secondary" onClick={() => void copyAll()} disabled={!query.data}>
                  {copied ? <Check size={16} aria-hidden /> : <Copy size={16} aria-hidden />}
                  {copied ? "Copied" : "Copy all"}
                </Button>
              </>
            )}
          </>
        }
      />
      <div className="page">
        {query.isLoading ? <Spinner label="Loading HR policies" /> : null}
        {query.isError ? (
          <p style={{ color: "var(--color-status-critical)" }}>Could not load HR policies.</p>
        ) : null}
        {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
        {doc ? (
          <article ref={bodyRef} className="hr-policies">
            <Card className="hr-policies__welcome" status="info">
              {editing ? (
                <div className="hr-policies__edit-stack">
                  <label className="form-field">
                    <span className="form-field__label">Heading</span>
                    <input
                      className="form-field__input"
                      value={doc.welcomeTitle}
                      onChange={(e) => patchWelcome({ welcomeTitle: e.target.value })}
                    />
                  </label>
                  <label className="form-field">
                    <span className="form-field__label">Subheading</span>
                    <input
                      className="form-field__input"
                      value={doc.welcomeSubtitle}
                      onChange={(e) => patchWelcome({ welcomeSubtitle: e.target.value })}
                    />
                  </label>
                </div>
              ) : (
                <>
                  <h2>{doc.welcomeTitle}</h2>
                  {doc.welcomeSubtitle ? <p>{doc.welcomeSubtitle}</p> : null}
                </>
              )}
            </Card>

            {doc.sections.map((section, si) => (
              <Card
                key={section.id}
                className={`hr-policies__section${confidentialClass(section.icon)}`}
                status={section.status}
              >
                {editing ? (
                  <label className="form-field hr-policies__section-title-field">
                    <span className="form-field__label">Section title</span>
                    <input
                      className="form-field__input"
                      value={section.title}
                      onChange={(e) => patchSection(si, { title: e.target.value })}
                    />
                  </label>
                ) : (
                  <h3>
                    {ICONS[section.icon]}
                    {section.title}
                  </h3>
                )}

                {editing ? (
                  <div className="hr-policies__edit-items">
                    {section.items.map((item, ii) => (
                      <div key={`${section.id}-edit-${ii}`} className="hr-policies__edit-item">
                        <label className="form-field">
                          <span className="form-field__label">Point {ii + 1}</span>
                          <textarea
                            className="form-field__input"
                            rows={item.quoted || item.text.length > 80 ? 3 : 2}
                            value={item.text}
                            onChange={(e) => patchItem(si, ii, { text: e.target.value })}
                          />
                        </label>
                        <label className="form-field">
                          <span className="form-field__label">Nested points (one per line)</span>
                          <textarea
                            className="form-field__input"
                            rows={2}
                            value={(item.children ?? []).join("\n")}
                            onChange={(e) =>
                              patchItem(si, ii, {
                                children: e.target.value.split("\n").map((l) => l.trim()).filter(Boolean),
                              })
                            }
                          />
                        </label>
                        <div className="hr-policies__edit-item-bar">
                          <label className="hr-policies__quote-toggle">
                            <input
                              type="checkbox"
                              checked={item.quoted}
                              onChange={(e) => patchItem(si, ii, { quoted: e.target.checked })}
                            />
                            Show as quote
                          </label>
                          <Button
                            variant="destructive"
                            disabled={section.items.length <= 1}
                            onClick={() => removeItem(si, ii)}
                          >
                            <Trash2 size={14} aria-hidden />
                            Remove
                          </Button>
                        </div>
                      </div>
                    ))}
                    <Button variant="secondary" onClick={() => addItem(si)}>
                      <Plus size={14} aria-hidden />
                      Add point
                    </Button>
                  </div>
                ) : (
                  <PolicyItems section={section} />
                )}
              </Card>
            ))}
          </article>
        ) : null}
      </div>
    </>
  );
}
