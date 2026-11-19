// Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Finding } from "@/lib/mock-data";

const severityConfig: Record<
  string,
  { label: string; className: string; dotColor: string }
> = {
  critical: {
    label: "Critical",
    className: "bg-[var(--color-severity-critical)]/10 text-[var(--color-severity-critical)] border-[var(--color-severity-critical)]/20",
    dotColor: "bg-[var(--color-severity-critical)]",
  },
  high: {
    label: "High",
    className: "bg-[var(--color-severity-high)]/10 text-[var(--color-severity-high)] border-[var(--color-severity-high)]/20",
    dotColor: "bg-[var(--color-severity-high)]",
  },
  medium: {
    label: "Medium",
    className: "bg-[var(--color-severity-medium)]/10 text-[var(--color-severity-medium)] border-[var(--color-severity-medium)]/20",
    dotColor: "bg-[var(--color-severity-medium)]",
  },
  low: {
    label: "Low",
    className: "bg-[var(--color-severity-low)]/10 text-[var(--color-severity-low)] border-[var(--color-severity-low)]/20",
    dotColor: "bg-[var(--color-severity-low)]",
  },
  info: {
    label: "Info",
    className: "bg-[var(--color-status-pass)]/10 text-[var(--color-status-pass)] border-[var(--color-status-pass)]/20",
    dotColor: "bg-[var(--color-status-pass)]",
  },
};

function inferPageReference(finding: Finding): string | null {
  // Try to extract page references from evidence text
  const combined = finding.evidence + " " + finding.description;
  const pageMatch = combined.match(/[Pp]age\s+(\d+)/);
  const sectionMatch = combined.match(/[Ss]ection\s+([\d.]+)/);
  const figureMatch = combined.match(/[Ff]igure\s+(\d+)/);

  const parts: string[] = [];
  if (pageMatch) parts.push(`Page ${pageMatch[1]}`);
  if (sectionMatch) parts.push(`Section ${sectionMatch[1]}`);
  if (figureMatch) parts.push(`Figure ${figureMatch[1]}`);

  return parts.length > 0 ? parts.join(", ") : null;
}

const statusConfig: Record<string, { label: string; icon: string; className: string; borderClass: string }> = {
  pass: {
    label: "PASS",
    icon: "✓",
    className: "bg-[var(--color-status-pass)] text-white",
    borderClass: "border-[var(--color-status-pass)]/30 bg-[var(--color-status-pass)]/3",
  },
  fail: {
    label: "FAIL",
    icon: "✗",
    className: "bg-[var(--color-status-fail)] text-white",
    borderClass: "border-[var(--color-status-fail)]/30 bg-[var(--color-status-fail)]/3",
  },
  warning: {
    label: "WARNING",
    icon: "⚠",
    className: "bg-[var(--color-status-warning)] text-white",
    borderClass: "border-[var(--color-status-warning)]/30 bg-[var(--color-status-warning)]/3",
  },
  // A substitution rescued the founding rule's failure.
  pass_via_substitution: {
    label: "PASS · SUBSTITUTION",
    icon: "↻",
    className: "bg-sky-600 text-white",
    borderClass: "border-sky-500/30 bg-sky-500/[0.04]",
  },
  // An exception fired; the founding rule doesn't apply here.
  not_applicable_via_exception: {
    label: "N/A · EXCEPTION",
    icon: "○",
    className: "bg-slate-500 text-white",
    borderClass: "border-slate-400/30 bg-slate-100/40 dark:bg-white/[0.03]",
  },
  // The document is silent on this rule: a coverage gap, NOT a failure —
  // neutral tone, excluded from the score.
  not_addressed: {
    label: "NOT ADDRESSED",
    icon: "–",
    className: "bg-slate-400 text-white",
    borderClass: "border-slate-300/40 bg-slate-50/60 dark:bg-white/[0.02]",
  },
};

export function FindingCard({
  finding,
  onOpenTrace,
  onOpenChat,
}: {
  finding: Finding;
  /** Open the live-log style trace drawer. */
  onOpenTrace?: (finding: Finding) => void;
  /** Open a corner chat scoped to this finding. */
  onOpenChat?: (finding: Finding) => void;
}) {
  const severity = severityConfig[finding.severity] || severityConfig.info;
  const status = statusConfig[finding.status] || statusConfig.warning;
  const pageReference = inferPageReference(finding);
  return (
    <Card className={`border ${status.borderClass}`}>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              {/* Status badge - prominent */}
              <span className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-bold ${status.className}`}>
                {status.icon} {status.label}
              </span>
              <Badge variant="outline" className={severity.className}>
                {severity.label}
              </Badge>
              <span className="text-[10px] font-mono text-muted-foreground">
                {finding.requirementId}
              </span>
              {pageReference && (
                <span className="text-xs text-muted-foreground">{pageReference}</span>
              )}
            </div>
            <CardTitle className="text-sm">{finding.title}</CardTitle>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {finding.description && finding.description !== finding.evidence && (
          <p className="text-sm text-muted-foreground">{finding.description}</p>
        )}

        <div className="space-y-2 border-l-2 border-border pl-3">
          <div>
            <span className="text-xs font-medium text-[var(--color-ink)]">
              Evidence
            </span>
            <p className="text-xs text-muted-foreground mt-0.5">
              {finding.evidence}
            </p>
          </div>
          <div>
            <span className="text-xs font-medium text-[var(--color-ink)]">
              Recommendation
            </span>
            <p className="text-xs text-muted-foreground mt-0.5">
              {finding.recommendation}
            </p>
          </div>
        </div>

        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer font-medium">Rule details</summary>
          <div className="mt-2 space-y-1 pl-3">
            {finding.pattern && finding.pattern !== finding.requirementId && <p>Pattern: {finding.pattern}</p>}
            {finding.ruleType && <p>Rule type: {finding.ruleType}</p>}
            {!!finding.alsoSeenPages?.length && (
              <p>Additional evidence: {finding.alsoSeenPages.join(", ")}</p>
            )}
            <Link href="/standards" className="inline-block underline">View all standards</Link>
          </div>
        </details>

        {/* Substitution rescue callout. The founding rule
            failed, but a substitution rule passed and rescued the
            layer's verdict. Show which one. */}
        {finding.status === "pass_via_substitution" && finding.viaRuleId && (
          <div className="rounded-md border border-sky-500/30 bg-sky-500/5 px-3 py-2 text-xs text-sky-700 dark:text-sky-300">
            <span className="font-semibold">Rescued by substitution:</span>{" "}
            <span className="font-mono">{finding.viaRuleId}</span> — the
            substitution rule passed, so this layer is treated as compliant.
          </div>
        )}

        {/* Exception applied callout. The founding rule
            doesn't apply because an exception fires for this scope. */}
        {finding.status === "not_applicable_via_exception" && finding.viaRuleId && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
            <span className="font-semibold">Excepted by:</span>{" "}
            <span className="font-mono">{finding.viaRuleId}</span> — this
            requirement is documented as not applicable for this design.
          </div>
        )}

        {/* Substitutions tried but did not pass. */}
        {finding.status === "fail" &&
          finding.triedSubstitutionIds &&
          finding.triedSubstitutionIds.length > 0 && (
            <div className="rounded-md border border-rose-500/20 bg-rose-500/5 px-3 py-2 text-xs text-rose-700 dark:text-rose-300">
              <span className="font-semibold">Substitutions tried:</span>{" "}
              {finding.triedSubstitutionIds.map((id, i) => (
                <span key={id}>
                  <span className="font-mono">{id}</span>
                  {i < finding.triedSubstitutionIds!.length - 1 ? ", " : ""}
                </span>
              ))}
              {" "}— none passed for this design.
            </div>
          )}

        {/* Trace drawer + per-finding chat triggers. The drawer renders
            a live-log style view; the chat button opens a corner panel
            scoped to this exact finding. */}
        {(finding.trace || onOpenChat) && (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            {finding.trace && onOpenTrace && (
              <button
                type="button"
                onClick={() => onOpenTrace(finding)}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10"
              >
                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6M9 8h6M5 4h14a2 2 0 012 2v12a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z" />
                </svg>
                View trace
              </button>
            )}
            {onOpenChat && (
              <button
                type="button"
                onClick={() => onOpenChat(finding)}
                className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-brand-primary)]/30 bg-[var(--color-brand-primary)]/5 px-2.5 py-1 text-[11px] font-medium text-[var(--color-brand-primary)] transition-colors hover:bg-[var(--color-brand-primary)]/10"
              >
                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                Ask why
              </button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
