function formatResolutionTime(totalMinutes) {
  if (totalMinutes < 60) {
    return `${Math.round(totalMinutes)} min`;
  }
  const hours = Math.round((totalMinutes / 60) * 10) / 10; // one decimal place
  return `${hours} hr${hours === 1 ? "" : "s"}`;
}

function computeStats(invoices) {
  const total = invoices.length;

  const byRecommendation = { approve: 0, escalate: 0, reject: 0, unavailable: 0 };
  for (const inv of invoices) {
    if (inv.ai_recommendation === "approve") byRecommendation.approve += 1;
    else if (inv.ai_recommendation === "escalate") byRecommendation.escalate += 1;
    else if (inv.ai_recommendation === "reject") byRecommendation.reject += 1;
    else byRecommendation.unavailable += 1;
  }

  // Override rate = human_override decisions / total reviewed invoices,
  // where "reviewed" = status is not pending_review. Exact definition
  // as specified — deliberately does NOT carve out invoices where the
  // AI had no recommendation to begin with (an earlier version of this
  // did exclude those; that's a different, stricter metric, not this
  // one — see the response this shipped in for why that changed).
  let reviewedCount = 0;
  let overriddenCount = 0;
  for (const inv of invoices) {
    if (inv.status !== "pending_review") {
      reviewedCount += 1;
      if (inv.human_override) overriddenCount += 1;
    }
  }
  const overrideRate = reviewedCount > 0 ? Math.round((overriddenCount / reviewedCount) * 100) : null;

  // Avg. resolution time = mean(reviewed_at - created_at) across
  // invoices that have both timestamps. The >= 0 guard is defensive —
  // reviewed_at should never precede created_at, but a time-based
  // average is exactly the kind of calculation where one bad or
  // clock-skewed row can silently distort the whole number, so a
  // negative duration is excluded rather than trusted.
  let totalResolutionMinutes = 0;
  let resolvedCount = 0;
  for (const inv of invoices) {
    if (inv.created_at && inv.reviewed_at) {
      const minutes = (new Date(inv.reviewed_at).getTime() - new Date(inv.created_at).getTime()) / 60000;
      if (minutes >= 0) {
        totalResolutionMinutes += minutes;
        resolvedCount += 1;
      }
    }
  }
  const avgResolutionMinutes = resolvedCount > 0 ? totalResolutionMinutes / resolvedCount : null;

  return { total, byRecommendation, overrideRate, reviewedCount, avgResolutionMinutes };
}

export default function SummaryBar({ invoices }) {
  const stats = computeStats(invoices);

  return (
    <section className="summary-bar" aria-label="Invoice summary">
      <div className="summary-stat">
        <span className="summary-value">{stats.total}</span>
        <span className="summary-label">Total invoices</span>
      </div>

      <div className="summary-stat">
        <span className="summary-value">{stats.byRecommendation.approve}</span>
        <span className="summary-label recommendation-approve">AI recommended approve</span>
      </div>

      <div className="summary-stat">
        <span className="summary-value">{stats.byRecommendation.escalate}</span>
        <span className="summary-label recommendation-escalate">AI recommended escalate</span>
      </div>

      <div className="summary-stat">
        <span className="summary-value">{stats.byRecommendation.reject}</span>
        <span className="summary-label recommendation-reject">AI recommended reject</span>
      </div>

      {stats.byRecommendation.unavailable > 0 && (
        <div className="summary-stat">
          <span className="summary-value">{stats.byRecommendation.unavailable}</span>
          <span className="summary-label recommendation-unavailable">AI unavailable</span>
        </div>
      )}

      <div className="summary-stat">
        <span className="summary-value">
          {stats.overrideRate === null ? "—" : `${stats.overrideRate}%`}
        </span>
        <span className="summary-label">
          Override rate{stats.reviewedCount > 0 ? ` (of ${stats.reviewedCount} reviewed)` : ""}
        </span>
      </div>

      <div className="summary-stat">
        <span className="summary-value">
          {stats.avgResolutionMinutes === null ? "—" : formatResolutionTime(stats.avgResolutionMinutes)}
        </span>
        <span className="summary-label">Avg. resolution time</span>
      </div>
    </section>
  );
}
