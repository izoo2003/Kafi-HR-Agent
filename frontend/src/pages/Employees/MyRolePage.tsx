import { useState } from "react";
import { PageHeader } from "../../components/layout/AppShell";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { Spinner } from "../../components/ui/Spinner";
import { FilePreviewModal, type FilePreviewRequest } from "../../components/domain/FilePreviewModal";
import { ApiError } from "../../api/client";
import { downloadDepartmentDocument } from "../../api/employees";
import { useMyDepartment } from "../../hooks/useEmployees";
import type { Department, DepartmentDocument, DepartmentDocumentKind } from "../../types/employees";
import "./MyRolePage.css";

function docsFor(dept: Department, kind: DepartmentDocumentKind): DepartmentDocument[] {
  return (dept.documents ?? []).filter((d) => d.kind === kind);
}

function CopySection({
  title,
  text,
  docs,
  onPreview,
}: {
  title: string;
  text: string | null;
  docs: DepartmentDocument[];
  onPreview: (doc: DepartmentDocument) => void;
}) {
  const body = (text ?? "").trim();
  const empty = !body && docs.length === 0;
  return (
    <Card className="my-role__section">
      <h2>{title}</h2>
      {empty ? (
        <p className="my-role__placeholder">HR has not added this for your department yet.</p>
      ) : null}
      {body ? <div className="my-role__copy">{body}</div> : null}
      {docs.length > 0 ? (
        <ul className="my-role__files">
          {docs.map((doc) => (
            <li key={doc.id}>
              <button type="button" className="my-role__file" onClick={() => onPreview(doc)}>
                {doc.originalFilename}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </Card>
  );
}

export function MyRolePage() {
  const dept = useMyDepartment();
  const [preview, setPreview] = useState<FilePreviewRequest | null>(null);

  function previewSaved(doc: DepartmentDocument) {
    setPreview({
      key: `dept-doc-${doc.id}`,
      title: doc.originalFilename,
      filename: doc.originalFilename,
      load: () => downloadDepartmentDocument(doc.departmentId, doc.id),
    });
  }

  const notLinked = dept.error instanceof ApiError && dept.error.status === 404;

  return (
    <>
      <PageHeader title="My role" breadcrumb="My role" />
      <div className="page my-role">
        {dept.isLoading ? <Spinner label="Loading your role" /> : null}
        {notLinked ? (
          <EmptyState
            title="No role assigned"
            description={
              dept.error instanceof ApiError
                ? dept.error.message
                : "Your account is not linked to a department. Ask HR to assign you a role."
            }
          />
        ) : null}
        {dept.isError && !notLinked ? (
          <EmptyState
            title="Could not load your role"
            description={
              dept.error instanceof ApiError
                ? dept.error.message
                : "Something went wrong, please try again."
            }
          />
        ) : null}
        {dept.data ? (
          <>
            <Card className="my-role__hero" status="info">
              <p className="my-role__kicker">Your department</p>
              <h2 className="my-role__dept">{dept.data.name}</h2>
              <p className="my-role__lede">
                Job description and standard operating procedures for this role.
              </p>
            </Card>
            <CopySection
              title="Job description"
              text={dept.data.jobDescriptionText}
              docs={docsFor(dept.data, "job_description")}
              onPreview={previewSaved}
            />
            <CopySection
              title="SOPs"
              text={dept.data.sopsText}
              docs={docsFor(dept.data, "sop")}
              onPreview={previewSaved}
            />
          </>
        ) : null}
      </div>
      {preview ? <FilePreviewModal preview={preview} onClose={() => setPreview(null)} /> : null}
    </>
  );
}
