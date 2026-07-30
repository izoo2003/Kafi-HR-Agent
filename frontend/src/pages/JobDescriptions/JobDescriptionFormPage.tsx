import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { FormField } from "../../components/ui/FormField";
import { useDepartments } from "../../hooks/useEmployees";
import {
  useCreateJobDescription,
  useCriteria,
  useJobDescription,
  useUpdateJobDescription,
} from "../../hooks/useJobDescriptions";
import { replaceCriteria as replaceCriteriaApi } from "../../api/jobDescriptions";
import { ApiError } from "../../api/client";
import type { ScoringCriteriaInput } from "../../types/cvScreening";

function skillRow(name = "", rating = 5): ScoringCriteriaInput {
  const skill = name.trim();
  return {
    criterionName: skill || name,
    weight: rating,
    scoringRules: {
      type: "keyword_match",
      config: {
        keywords: skill ? [skill] : [],
        match_mode: "any",
        points_per_match: 10,
        max_points: 10,
        proficiency: rating,
      },
    },
  };
}

/** Migrate old 0–1 weights to a 1–10 rating for the form. */
function toRating(weight: number): number {
  if (weight > 1) return Math.min(10, Math.max(1, Math.round(weight)));
  return Math.min(10, Math.max(1, Math.round(weight * 10) || 1));
}

export function JobDescriptionFormPage() {
  const { id } = useParams();
  const isEdit = Boolean(id && id !== "new");
  const jobId = isEdit ? Number(id) : 0;
  const navigate = useNavigate();
  const departments = useDepartments();
  const existing = useJobDescription(jobId);
  const createJob = useCreateJobDescription();
  const updateJob = useUpdateJobDescription(jobId);
  const criteriaQ = useCriteria(jobId);

  const [title, setTitle] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [descriptionText, setDescriptionText] = useState("");
  const [requirementsText, setRequirementsText] = useState("");
  const [status, setStatus] = useState<"draft" | "open" | "closed">("draft");
  const [skills, setSkills] = useState<ScoringCriteriaInput[]>([
    skillRow("Python", 8),
    skillRow("Communication", 5),
  ]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!existing.data) return;
    setTitle(existing.data.title);
    setDepartmentId(String(existing.data.departmentId));
    setDescriptionText(existing.data.descriptionText);
    setRequirementsText(existing.data.requirementsText ?? "");
    setStatus(existing.data.status as "draft" | "open" | "closed");
  }, [existing.data]);

  useEffect(() => {
    if (!criteriaQ.data?.length) return;
    setSkills(
      criteriaQ.data.map((c) => skillRow(c.criterionName, toRating(Number(c.weight)))),
    );
  }, [criteriaQ.data]);

  function updateSkill(idx: number, name: string, rating: number) {
    const next = [...skills];
    next[idx] = skillRow(name, rating);
    setSkills(next);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const cleaned = skills
      .map((s) => skillRow(s.criterionName.trim(), toRating(Number(s.weight))))
      .filter((s) => s.criterionName.length > 0);
    if (cleaned.length === 0) {
      setError("Add at least one skill with a rating from 1 to 10");
      return;
    }
    for (const s of cleaned) {
      if (s.weight < 1 || s.weight > 10) {
        setError(`Level for "${s.criterionName}" must be between 1 (very low) and 10 (expert)`);
        return;
      }
    }
    try {
      const payload = {
        title: title.trim(),
        departmentId: Number(departmentId),
        descriptionText: descriptionText.trim(),
        requirementsText: requirementsText.trim() || undefined,
        status,
      };
      const job = isEdit
        ? await updateJob.mutateAsync(payload)
        : await createJob.mutateAsync(payload);
      await replaceCriteriaApi(job.id, cleaned);
      navigate(`/job-descriptions/${job.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    }
  }

  return (
    <>
      <PageHeader
        title={isEdit ? "Edit Job Description" : "New Job Description"}
        breadcrumb="Job Descriptions / Form"
      />
      <div className="page">
        <form className="card" onSubmit={onSubmit} style={{ display: "grid", gap: "var(--space-4)" }}>
          {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
          <FormField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <label className="form-field">
            <span className="form-field__label">Department</span>
            <select
              className="form-field__input"
              value={departmentId}
              onChange={(e) => setDepartmentId(e.target.value)}
              required
            >
              <option value="">Select…</option>
              {(departments.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span className="form-field__label">Description</span>
            <textarea
              className="form-field__input"
              rows={5}
              value={descriptionText}
              onChange={(e) => setDescriptionText(e.target.value)}
              required
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">Requirements</span>
            <textarea
              className="form-field__input"
              rows={3}
              value={requirementsText}
              onChange={(e) => setRequirementsText(e.target.value)}
            />
          </label>
          <label className="form-field">
            <span className="form-field__label">Status</span>
            <select
              className="form-field__input"
              value={status}
              onChange={(e) => setStatus(e.target.value as typeof status)}
            >
              <option value="draft">Draft</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
          </label>

          <div>
            <h3 style={{ marginBottom: "var(--space-2)" }}>Skills</h3>
            <p style={{ marginTop: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
              Rate required proficiency: <strong>1 = very low</strong>, <strong>10 = expert</strong>.
            </p>
            {skills.map((s, idx) => (
              <div
                key={idx}
                style={{
                  display: "grid",
                  gap: "var(--space-2)",
                  gridTemplateColumns: "1fr 160px auto",
                  alignItems: "end",
                  marginBottom: "var(--space-3)",
                }}
              >
                <FormField
                  label="Skill"
                  value={s.criterionName}
                  onChange={(e) => updateSkill(idx, e.target.value, toRating(Number(s.weight)))}
                  required
                  placeholder="e.g. Python"
                />
                <FormField
                  label="Level (1–10)"
                  type="number"
                  min={1}
                  max={10}
                  step={1}
                  value={String(toRating(Number(s.weight)))}
                  onChange={(e) =>
                    updateSkill(idx, s.criterionName, toRating(Number(e.target.value) || 1))
                  }
                  required
                  hint="1 low · 10 expert"
                />
                <div style={{ paddingBottom: 2 }}>
                  <Button
                    type="button"
                    variant="destructive"
                    onClick={() => setSkills(skills.filter((_, i) => i !== idx))}
                    disabled={skills.length <= 1}
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ))}
            <Button type="button" variant="secondary" onClick={() => setSkills([...skills, skillRow("", 5)])}>
              Add skill
            </Button>
          </div>

          <Button type="submit" variant="primary">
            Save Job Description
          </Button>
        </form>
      </div>
    </>
  );
}
