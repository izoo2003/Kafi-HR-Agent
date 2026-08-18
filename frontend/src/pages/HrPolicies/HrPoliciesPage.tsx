import { useRef, useState } from "react";
import {
  CalendarOff,
  Check,
  ClipboardList,
  Copy,
  FileText,
  Lock,
  Timer,
} from "lucide-react";
import { PageHeader } from "../../components/layout/AppShell";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import "./HrPoliciesPage.css";

export function HrPoliciesPage() {
  const bodyRef = useRef<HTMLElement>(null);
  const [copied, setCopied] = useState(false);

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

  return (
    <>
      <PageHeader
        title="HR Policies"
        breadcrumb="HR Policies"
        actions={
          <Button variant="secondary" onClick={() => void copyAll()}>
            {copied ? <Check size={16} aria-hidden /> : <Copy size={16} aria-hidden />}
            {copied ? "Copied" : "Copy all"}
          </Button>
        }
      />
      <div className="page">
        <article ref={bodyRef} className="hr-policies">
          <Card className="hr-policies__welcome" status="info">
            <h2>Welcome to KAFI Team</h2>
            <p>HR Major Highlight Points</p>
          </Card>

          <Card className="hr-policies__section" status="info">
            <h3>
              <FileText size={18} strokeWidth={1.75} aria-hidden />
              Required Documents
            </h3>
            <ol>
              <li>Updated CV with photo &amp; CNIC/ID copy</li>
              <li>CNIC/ID copy of one first blood relative</li>
              <li>
                Five references in total:
                <ul className="hr-policies__nested">
                  <li>One previous job reference (Director-level preferred)</li>
                  <li>One blood relative reference</li>
                  <li>Three professional references</li>
                </ul>
              </li>
              <li>Resignation letter from last job with official receiving</li>
              <li>Last job salary slip (any one month)</li>
            </ol>
          </Card>

          <Card className="hr-policies__section" status="warning">
            <h3>
              <Timer size={18} strokeWidth={1.75} aria-hidden />
              Office Timings &amp; Attendance
            </h3>
            <ul>
              <li>Office Timing: 9:30 AM to 6:30 PM</li>
              <li>3 late arrivals = 1 leave deduction</li>
              <li>Second Saturday of every month is an official holiday</li>
              <li>
                Government-gazetted holidays (e.g., Eid, 14th August, 25th December) will be
                observed
              </li>
              <li>
                Non-regular or emergency government holidays will not be observed unless
                officially approved and circulated by KAFI
              </li>
            </ul>
          </Card>

          <Card className="hr-policies__section" status="neutral">
            <h3>
              <ClipboardList size={18} strokeWidth={1.75} aria-hidden />
              SOP
            </h3>
            <div className="hr-policies__sop">
              <p>All KPI are daily sent by WhatsApp/ SMS / emails</p>
              <p>Daily tasks must be written on Computer Sticky notes</p>
              <p>
                All SOP as per JOB description, dress code, and ethical policy must be followed
              </p>
            </div>
          </Card>

          <Card className="hr-policies__section" status="on_leave">
            <h3>
              <CalendarOff size={18} strokeWidth={1.75} aria-hidden />
              Leave Policy
            </h3>
            <ul>
              <li>No leaves allowed during the first 3-month probation period</li>
              <li>
                After completing 7 months, employees receive 12 annual leaves per year
                (including sick leave)
              </li>
              <li>1 Saturday off every month = 12 additional holidays per year</li>
              <li>
                Total: 24 company holidays annually + all official government-gazetted holidays
              </li>
              <li>
                <p className="hr-policies__quote">
                  “Non-regular or emergency Government-announced holidays will not be observed
                  unless officially approved and formally communicated by KAFI Management.”
                </p>
              </li>
              <li>All leave requests must be made in advance</li>
              <li>Unapproved absence will be counted as Leave Without Pay (LWP)</li>
            </ul>
          </Card>

          <Card className="hr-policies__section hr-policies__confidential" status="critical">
            <h3>
              <Lock size={18} strokeWidth={1.75} aria-hidden />
              Confidentiality Clause
            </h3>
            <p>
              All company data, documents, contacts, pricing, client details, and internal
              information are strictly confidential. Any unauthorized sharing or misuse is a
              serious violation and may result in immediate termination, financial penalties,
              recovery of damages, and legal action under applicable laws
            </p>
          </Card>
        </article>
      </div>
    </>
  );
}
