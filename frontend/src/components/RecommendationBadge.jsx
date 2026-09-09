const LABELS = { approve: "Approve", escalate: "Escalate", reject: "Reject" };

export default function RecommendationBadge({ recommendation, rationale }) {
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

  // Native title attribute = simplest option that satisfies "hover
  // tooltip" without new state/interaction logic. Trade-off worth
  // knowing: it doesn't work on touch devices (no hover), and there's
  // a small delay before browsers show it. If that turns out to
  // matter, the click-to-expand alternative is a bigger but more
  // reliable change — this was the "keep it simple" pick, not the
  // only valid one.
  return (
    <span className={`badge badge-${recommendation}`} title={rationale || undefined}>
      {LABELS[recommendation] || recommendation}
    </span>
  );
}
