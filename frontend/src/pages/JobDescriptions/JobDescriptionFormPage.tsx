import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { FormField } from "../../components/ui/FormField";
import { LinkedInPostResults } from "../../components/domain/LinkedInPostResults";
import { useDepartments } from "../../hooks/useEmployees";
import {
  useApplicationFormUrl,
  useCreateJobDescription,
  useCriteria,
  useDeleteJobImage,
  useGenerateJobPostingAiDraft,
  useJobDescription,
  useLinkedInAccounts,
  useUpdateJobDescription,
} from "../../hooks/useJobDescriptions";
import { replaceCriteria as replaceCriteriaApi, uploadJobImages } from "../../api/jobDescriptions";
import { ApiError } from "../../api/client";
import type { LinkedInPostResult, ScoringCriteriaInput } from "../../types/cvScreening";
import { JobPostingImageGallery, MAX_JOB_IMAGES } from "../../components/domain/JobPostingImages";
import {
  clearJobDescriptionFormDraft,
  hasMeaningfulJobDescriptionDraft,
  loadJobDescriptionFormDraft,
  saveJobDescriptionFormDraft,
  type JobDescriptionFormDraftPayload,
} from "../../lib/jobDescriptionFormDraft";

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
  const aiDraft = useGenerateJobPostingAiDraft();
  const applicationForm = useApplicationFormUrl();
  const linkedinAccounts = useLinkedInAccounts();
  const criteriaQ = useCriteria(jobId);
  const deleteImage = useDeleteJobImage(jobId);

  const draftKey: number | "new" = isEdit ? jobId : "new";
  const emptySkills = [skillRow("", 5)];

  const draftBootstrap = useMemo((): {
    draftKey: number | "new";
    restored: boolean;
    title: string;
    departmentId: string;
    descriptionText: string;
    requirementsText: string;
    status: "draft" | "open" | "closed";
    skills: ScoringCriteriaInput[];
    selectedLinkedin: string[];
  } => {
    const draft = loadJobDescriptionFormDraft(draftKey);
    if (!draft) {
      return {
        draftKey,
        restored: false,
        title: "",
        departmentId: "",
        descriptionText: "",
        requirementsText: "",
        status: "draft",
        skills: emptySkills,
        selectedLinkedin: [],
      };
    }
    return {
      draftKey,
      restored: true,
      title: draft.title ?? "",
      departmentId: draft.departmentId ?? "",
      descriptionText: draft.descriptionText ?? "",
      requirementsText: draft.requirementsText ?? "",
      status: (draft.status ?? "draft") as "draft" | "open" | "closed",
      skills: Array.isArray(draft.skills) && draft.skills.length > 0 ? draft.skills : emptySkills,
      selectedLinkedin: Array.isArray(draft.selectedLinkedin) ? draft.selectedLinkedin : [],
    };
  }, [draftKey]);

  const draftRestoredRef = useRef(draftBootstrap.restored);

  const [title, setTitle] = useState(draftBootstrap.title);
  const [departmentId, setDepartmentId] = useState(draftBootstrap.departmentId);
  const [descriptionText, setDescriptionText] = useState(draftBootstrap.descriptionText);
  const [requirementsText, setRequirementsText] = useState(draftBootstrap.requirementsText);
  const [status, setStatus] = useState<"draft" | "open" | "closed">(draftBootstrap.status);
  const [skills, setSkills] = useState<ScoringCriteriaInput[]>(draftBootstrap.skills);
  const [error, setError] = useState<string | null>(null);
  const [aiMessage, setAiMessage] = useState<string | null>(null);
  const [linkedinPromptOpen, setLinkedinPromptOpen] = useState(false);
  const [linkedinPhase, setLinkedinPhase] = useState<"pick" | "posting" | "result">("pick");
  const [selectedLinkedin, setSelectedLinkedin] = useState<string[]>(draftBootstrap.selectedLinkedin);
  const [linkedinResults, setLinkedinResults] = useState<LinkedInPostResult[]>([]);
  const [postedJobId, setPostedJobId] = useState<number | null>(null);
  const [pendingImages, setPendingImages] = useState<File[]>([]);
  const [pendingPreviews, setPendingPreviews] = useState<string[]>([]);
  const [draftMessage, setDraftMessage] = useState<string | null>(
    draftBootstrap.restored ? "Restored unsaved job posting draft from your last session." : null,
  );

  const formUrl =
    applicationForm.data?.applicationFormUrl ||
    existing.data?.applicationFormUrl ||
    null;

  async function onGenerateAiDraft() {
    setError(null);
    setAiMessage(null);
    if (!title.trim() || !departmentId) {
      setError("Enter a title and select a department before running AI Analyzer");
      return;
    }
    const hasExisting =
      descriptionText.trim().length > 0 ||
      requirementsText.trim().length > 0 ||
      skills.some((s) => s.criterionName.trim().length > 0);
    if (hasExisting) {
      const ok = window.confirm(
        "AI Analyzer will replace Description, Requirements, and Skills. Continue?",
      );
      if (!ok) return;
    }
    try {
      const draft = await aiDraft.mutateAsync({
        title: title.trim(),
        departmentId: Number(departmentId),
      });
      setDescriptionText(draft.descriptionText);
      setRequirementsText(draft.requirementsText);
      if (draft.skills?.length) {
        setSkills(draft.skills.map((s) => skillRow(s.name, toRating(s.level))));
      }
      setAiMessage(
        "AI Analyzer filled Description (including hashtags), Requirements, and Skills — review before saving.",
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "AI Analyzer failed");
    }
  }

  useEffect(() => {
    if (!existing.data) return;
    if (draftRestoredRef.current) return; // keep unsaved draft instead of overwriting from API
    setTitle(existing.data.title);
    setDepartmentId(String(existing.data.departmentId));
    setDescriptionText(existing.data.descriptionText);
    setRequirementsText(existing.data.requirementsText ?? "");
    setStatus(existing.data.status as "draft" | "open" | "closed");
  }, [existing.data]);

  useEffect(() => {
    const urls = pendingImages.map((file) => URL.createObjectURL(file));
    setPendingPreviews(urls);
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, [pendingImages]);

  useEffect(() => {
    const names = (linkedinAccounts.data ?? []).map((a) => a.name);
    if (names.length && !draftRestoredRef.current) setSelectedLinkedin(names);
  }, [linkedinAccounts.data]);

  useEffect(() => {
    if (!criteriaQ.data?.length) return;
    if (draftRestoredRef.current) return; // keep unsaved draft instead of overwriting from API
    setSkills(
      criteriaQ.data.map((c) => skillRow(c.criterionName, toRating(Number(c.weight)))),
    );
  }, [criteriaQ.data]);

  const skipPersistRef = useRef(true);
  useEffect(() => {
    // Don't persist before edit page data arrives (unless we restored a draft already).
    if (isEdit && !existing.data && !draftRestoredRef.current) return;
    if (skipPersistRef.current) {
      skipPersistRef.current = false;
      return;
    }

    const draftPayload: Omit<JobDescriptionFormDraftPayload, "version" | "savedAt"> = {
      title,
      departmentId,
      descriptionText,
      requirementsText,
      status,
      skills,
      selectedLinkedin,
    };

    if (!hasMeaningfulJobDescriptionDraft(draftPayload)) {
      clearJobDescriptionFormDraft(draftKey);
      return;
    }

    const timer = window.setTimeout(() => {
      saveJobDescriptionFormDraft(draftKey, draftPayload);
    }, 400);
    return () => window.clearTimeout(timer);
  }, [
    title,
    departmentId,
    descriptionText,
    requirementsText,
    status,
    skills,
    selectedLinkedin,
    isEdit,
    existing.data,
    draftKey,
  ]);

  function updateSkill(idx: number, name: string, rating: number) {
    const next = [...skills];
    next[idx] = skillRow(name, rating);
    setSkills(next);
  }

  async function saveJob(
    linkedinAccountNames?: string[],
    options?: { forceOpen?: boolean; showLinkedInResult?: boolean },
  ) {
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
      const existingImageCount = existing.data?.imagePaths?.length ?? 0;
      if (existingImageCount + pendingImages.length > MAX_JOB_IMAGES) {
        setError(`At most ${MAX_JOB_IMAGES} images per job posting`);
        return;
      }
      const payload = {
        title: title.trim(),
        departmentId: Number(departmentId),
        descriptionText: descriptionText.trim(),
        requirementsText: requirementsText.trim() || undefined,
        status: options?.forceOpen ? "open" : status,
        linkedinAccountNames,
      };
      const job = isEdit
        ? await updateJob.mutateAsync(payload)
        : await createJob.mutateAsync(payload);
      await replaceCriteriaApi(job.id, cleaned);
      if (pendingImages.length > 0) {
        await uploadJobImages(job.id, pendingImages);
        setPendingImages([]);
      }
      // Job is now persisted — drop any local unsaved draft.
      clearJobDescriptionFormDraft("new");
      clearJobDescriptionFormDraft(job.id);
      setDraftMessage(null);
      if (options?.showLinkedInResult) {
        setPostedJobId(job.id);
        const selected = new Set(selectedLinkedin);
        const rows = (job.linkedinPosts ?? []).filter((post) => selected.has(post.account));
        setLinkedinResults(rows.length ? rows : (job.linkedinPosts ?? []));
        setLinkedinPhase("result");
        setLinkedinPromptOpen(true);
        return;
      }
      navigate(`/job-descriptions/${job.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
      if (options?.showLinkedInResult) {
        setLinkedinPhase("pick");
      }
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    await saveJob();
  }

  async function onPostToLinkedIn() {
    setError(null);
    setAiMessage(null);
    if (!title.trim() || !departmentId || !descriptionText.trim()) {
      setError("Complete the job posting before posting to LinkedIn.");
      return;
    }
    const accounts = linkedinAccounts.data ?? [];
    if (accounts.length === 0) {
      setError("No LinkedIn accounts are configured for posting.");
      return;
    }
    setLinkedinPhase("pick");
    setLinkedinPromptOpen(true);
  }

  function toggleLinkedinAccount(name: string) {
    setSelectedLinkedin((current) =>
      current.includes(name) ? current.filter((n) => n !== name) : [...current, name],
    );
  }

  return (
    <>
      <PageHeader
        title={isEdit ? "Edit Job Posting" : "New Job Posting"}
        breadcrumb="Job Postings / Form"
      />
      <div className="page">
        <form className="card" onSubmit={onSubmit} style={{ display: "grid", gap: "var(--space-4)" }}>
          {error ? <p style={{ color: "var(--color-status-critical)" }}>{error}</p> : null}
          {draftMessage ? (
            <p style={{ color: "var(--color-status-info)", margin: 0 }}>{draftMessage}</p>
          ) : null}
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

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "var(--space-3)",
              alignItems: "center",
              padding: "var(--space-3)",
              background: "var(--color-accent-subtle)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-border)",
            }}
          >
            <div style={{ flex: "1 1 220px" }}>
              <strong style={{ display: "block", marginBottom: 4 }}>AI Analyzer</strong>
              <span style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
                Generates description (with relevant hashtags), requirements, and skills for this
                title — and appends the Google Form apply link to the description.
              </span>
            </div>
            <Button
              type="button"
              variant="primary"
              disabled={aiDraft.isPending || !title.trim() || !departmentId}
              onClick={onGenerateAiDraft}
            >
              {aiDraft.isPending ? "Generating…" : "Generate with AI"}
            </Button>
          </div>
          {aiMessage ? (
            <p style={{ color: "var(--color-status-info)", margin: 0 }}>{aiMessage}</p>
          ) : null}

          <div
            className="card"
            style={{
              padding: "var(--space-4)",
              background: "var(--color-surface-alt)",
              border: "1px solid var(--color-border)",
            }}
          >
            <h3 style={{ marginTop: 0, marginBottom: "var(--space-2)", fontSize: "var(--text-base)" }}>
              Google Form — submit details &amp; CV
            </h3>
            <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
              Candidates should submit their details and CV through this form. The link is also added
              into the job description when you use AI Analyzer (and on save if missing).
            </p>
            {formUrl ? (
              <p style={{ margin: "var(--space-3) 0 0", wordBreak: "break-all" }}>
                <a href={formUrl} target="_blank" rel="noreferrer" style={{ color: "var(--color-accent)" }}>
                  {formUrl}
                </a>
              </p>
            ) : (
              <p style={{ margin: "var(--space-3) 0 0", color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
                Form URL not configured yet (`GOOGLE_FORM_URL`).
              </p>
            )}
          </div>

          <label className="form-field">
            <span className="form-field__label">Description</span>
            <textarea
              className="form-field__input"
              rows={5}
              value={descriptionText}
              onChange={(e) => setDescriptionText(e.target.value)}
              required
            />
            <span className="form-field__hint" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
              AI Analyzer ends the description with hiring hashtags. You can edit them before saving.
            </span>
          </label>
          <label className="form-field">
            <span className="form-field__label">Posting images</span>
            <input
              className="form-field__input"
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              multiple
              onChange={(e) => {
                const picked = Array.from(e.target.files ?? []);
                e.target.value = "";
                if (!picked.length) return;
                setPendingImages((current) => {
                  const existingCount = existing.data?.imagePaths?.length ?? 0;
                  const room = Math.max(0, MAX_JOB_IMAGES - existingCount - current.length);
                  return [...current, ...picked.slice(0, room)];
                });
              }}
            />
            <span className="form-field__hint" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
              Optional. PNG, JPG, WEBP, or GIF — up to {MAX_JOB_IMAGES} images. New files upload when you save.
            </span>
          </label>
          {isEdit && (existing.data?.imagePaths?.length ?? 0) > 0 ? (
            <JobPostingImageGallery
              jobId={jobId}
              count={existing.data?.imagePaths?.length ?? 0}
              onRemove={(index) => {
                void deleteImage.mutateAsync(index).catch((err) => {
                  setError(err instanceof ApiError ? err.message : "Could not remove image");
                });
              }}
            />
          ) : null}
          {pendingPreviews.length > 0 ? (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                gap: "var(--space-3)",
              }}
            >
              {pendingPreviews.map((url, index) => (
                <figure
                  key={`${pendingImages[index]?.name ?? index}-${index}`}
                  style={{
                    margin: 0,
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-sm)",
                    overflow: "hidden",
                    background: "var(--color-surface-alt)",
                  }}
                >
                  <img
                    src={url}
                    alt={pendingImages[index]?.name ?? `New image ${index + 1}`}
                    style={{ width: "100%", height: 120, objectFit: "cover", display: "block" }}
                  />
                  <div style={{ padding: "var(--space-2)" }}>
                    <Button
                      type="button"
                      variant="destructive"
                      onClick={() =>
                        setPendingImages((current) => current.filter((_, i) => i !== index))
                      }
                    >
                      Remove
                    </Button>
                  </div>
                </figure>
              ))}
            </div>
          ) : null}
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
            <span className="form-field__hint" style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
              Status controls visibility. LinkedIn posting is now triggered only by the separate
              <strong> Post to LinkedIn </strong>
              button.
            </span>
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

          <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
            <Button type="submit" variant="primary">
              Save Job Posting
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={createJob.isPending || updateJob.isPending || linkedinAccounts.isLoading}
              onClick={onPostToLinkedIn}
            >
              Post to LinkedIn
            </Button>
          </div>
        </form>
      </div>
      {linkedinPromptOpen ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="linkedin-post-title"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(16, 24, 40, 0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "var(--space-5)",
            zIndex: 40,
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: 560,
              width: "100%",
              boxShadow: "0 8px 24px rgba(16,24,40,0.12)",
              display: "grid",
              gap: "var(--space-4)",
            }}
          >
            {linkedinPhase === "posting" ? (
              <>
                <h2 id="linkedin-post-title" style={{ margin: 0, fontSize: "var(--text-lg)" }}>
                  Posting to LinkedIn
                </h2>
                <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                  Publishing this job to the selected accounts. This can take a few seconds.
                </p>
              </>
            ) : null}
            {linkedinPhase === "result" ? (
              <>
                <h2 id="linkedin-post-title" style={{ margin: 0, fontSize: "var(--text-lg)" }}>
                  LinkedIn post confirmation
                </h2>
                {linkedinResults.length > 0 ? (
                  <LinkedInPostResults posts={linkedinResults} />
                ) : (
                  <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}>
                    The job was saved, but LinkedIn did not return post results. Open the job to retry.
                  </p>
                )}
                <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", justifyContent: "flex-end" }}>
                  <Button
                    type="button"
                    variant="primary"
                    onClick={() => navigate(`/job-descriptions/${postedJobId ?? jobId}`)}
                  >
                    View job posting
                  </Button>
                </div>
              </>
            ) : null}
            {linkedinPhase === "pick" ? (
              <>
                <div>
                  <h2 id="linkedin-post-title" style={{ margin: 0, fontSize: "var(--text-lg)" }}>
                    This will be posted on LinkedIn
                  </h2>
                  <p
                    style={{
                      margin: "var(--space-2) 0 0",
                      color: "var(--color-text-secondary)",
                      fontSize: "var(--text-sm)",
                    }}
                  >
                    Select the accounts that should publish this job. Choose all three, or only the
                    profiles you want.
                  </p>
                </div>
                <div style={{ display: "grid", gap: "var(--space-3)" }}>
                  {(linkedinAccounts.data ?? []).map((account) => (
                    <label
                      key={account.name}
                      style={{
                        display: "flex",
                        gap: "var(--space-3)",
                        alignItems: "center",
                        padding: "var(--space-3)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-sm)",
                        background: selectedLinkedin.includes(account.name)
                          ? "var(--color-accent-subtle)"
                          : "var(--color-surface)",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedLinkedin.includes(account.name)}
                        onChange={() => toggleLinkedinAccount(account.name)}
                      />
                      <span>{account.label}</span>
                    </label>
                  ))}
                </div>
                {selectedLinkedin.length === 0 ? (
                  <p style={{ margin: 0, color: "var(--color-status-warning)", fontSize: "var(--text-sm)" }}>
                    Select at least one account to post, or save without posting.
                  </p>
                ) : null}
                <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", justifyContent: "flex-end" }}>
                  <Button type="button" variant="secondary" onClick={() => setLinkedinPromptOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={async () => {
                      setLinkedinPromptOpen(false);
                      await saveJob([]);
                    }}
                  >
                    Save without posting
                  </Button>
                  <Button
                    type="button"
                    variant="primary"
                    disabled={selectedLinkedin.length === 0 || createJob.isPending || updateJob.isPending}
                    onClick={async () => {
                      setLinkedinPhase("posting");
                      await saveJob(selectedLinkedin, { forceOpen: true, showLinkedInResult: true });
                    }}
                  >
                    Post to selected accounts
                  </Button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
