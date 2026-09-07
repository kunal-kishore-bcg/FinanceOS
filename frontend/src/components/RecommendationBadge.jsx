const LABELS = { approve: "Approve", escalate: "Escalate", reject: "Reject" };

export default function RecommendationBadge({ recommendation }) {
  if (!recommendation) {
    return (
      <span
        className="badge badge-unavailable"
        title="The AI service did not return a recommendation for this invoice — it needs manual review."
      >
        AI unavailable — manual review required
      </span>
    );
  }

  return <span className={`badge badge-${recommendation}`}>{LABELS[recommendation] || recommendation}</span>;
}
