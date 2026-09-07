function computeStats(invoices) {
  const total = invoices.length;

  const byRecommendation = { approve: 0, escalate: 0, reject: 0, unavailable: 0 };
  for (const inv of invoices) {
    if (inv.ai_recommendation === "approve") byRecommendation.approve += 1;
    else if (inv.ai_recommendation === "escalate") byRecommendation.escalate += 1;
    else if (inv.ai_recommendation === "reject") byRecommendation.reject += 1;
    else byRecommendation.unavailable += 1;
  }

  // Override rate = invoices where a human changed the AI's call,
  // out of invoices where the AI actually made a call AND a human has
  // reviewed it. Invoices where the AI failed (no recommendation) are
  // excluded from both sides on purpose — there's nothing to
  // "override" if the AI never gave an opinion, and folding those in
  // would understate the true rate.
  let reviewedWithAiOpinion = 0;
  let overridden = 0;
  for (const inv of invoices) {
    const wasReviewed = Boolean(inv.reviewed_by);
    const aiHadOpinion = Boolean(inv.ai_recommendation);
    if (wasReviewed && aiHadOpinion) {
      reviewedWithAiOpinion += 1;
      if (inv.human_override) overridden += 1;
    }
  }
  const overrideRate =
    reviewedWithAiOpinion > 0 ? Math.round((overridden / reviewedWithAiOpinion) * 100) : null;

  return { total, byRecommendation, overrideRate, reviewedWithAiOpinion };
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
          Override rate
          {stats.reviewedWithAiOpinion > 0 ? ` (of ${stats.reviewedWithAiOpinion} reviewed)` : ""}
        </span>
      </div>
    </section>
  );
}
