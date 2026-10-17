import React from "react";
import "./OverviewGuide.css";

export function StatisticsGuide({ onOpenOperations, onOpenInsights }) {
  return (
    <section
      className="panel overview-guide"
      aria-labelledby="overview-guide-title"
    >
      <div className="overview-guide-intro">
        <span className="overview-guide-eyebrow">Start here</span>
        <h2 id="overview-guide-title">
          See delays. Spot changes. Choose what to investigate.
        </h2>
        <p>
          ResponseWatch helps dispatch supervisors compare ambulance response
          times across zones. Response time starts at dispatch and ends at
          arrival on scene.
        </p>
      </div>
      <ol className="overview-guide-steps">
        <li>
          <span className="overview-guide-number" aria-hidden="true">
            1
          </span>
          <div>
            <h3>Check the service target</h3>
            <p>
              The late percentage shows how often completed calls miss your
              target. The p90 shows how long the slower responses take.
            </p>
          </div>
        </li>
        <li>
          <span className="overview-guide-number" aria-hidden="true">
            2
          </span>
          <div>
            <h3>Look for unusual changes</h3>
            <p>
              I–MR charts compare individual responses and changes between calls
              with a fixed earlier reference. A signal is a reason to
              investigate.
            </p>
          </div>
        </li>
        <li>
          <span className="overview-guide-number" aria-hidden="true">
            3
          </span>
          <div>
            <h3>Investigate, then follow up</h3>
            <p>
              Use the fault-tree guide to ask questions, check recorded context,
              and assign a review action.
            </p>
          </div>
        </li>
      </ol>
      <div className="overview-guide-footer">
        <p>
          <strong>Stable does not mean fast enough.</strong> A process can be
          predictable and still miss its service target. A signal alone does not
          prove a cause.
        </p>
        {(onOpenOperations || onOpenInsights) && (
          <div className="overview-guide-actions">
            {onOpenOperations && (
              <button type="button" onClick={onOpenOperations}>
                Log or track a call <span aria-hidden="true">→</span>
              </button>
            )}
            {onOpenInsights && (
              <button type="button" onClick={onOpenInsights}>
                Explore supporting analysis <span aria-hidden="true">→</span>
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

const paths = [
  {
    title: "Unit mobilization",
    question: "Was a unit able to get moving promptly after dispatch?",
    examples:
      "Check availability, crew turnout, and any reassignment after the dispatch timestamp.",
  },
  {
    title: "Travel to the scene",
    question: "Did the journey take longer than expected?",
    examples:
      "Check travel distance, congestion, road closures, and routing records.",
  },
  {
    title: "Finding or accessing the scene",
    question: "Was arrival delayed by location or access difficulties?",
    examples:
      "Check address information and access records, using the agency’s exact definition of arrival.",
  },
];

export function FaultTreeGuide({ target = 8, selected, onOpenInsights }) {
  const context = selected?.delay_patterns;
  const threshold = Number(target);
  const targetLabel = Number.isFinite(threshold)
    ? threshold
    : "the selected target";
  return (
    <section className="panel fault-tree" aria-labelledby="fault-tree-title">
      <div className="fault-tree-heading">
        <div>
          <span className="overview-guide-eyebrow">
            What could explain a delay?
          </span>
          <h3 id="fault-tree-title">
            Qualitative fault tree · investigation guide
          </h3>
          <p>
            Possible paths to investigate, not confirmed causes or calculated
            failure probabilities.
          </p>
        </div>
        {selected?.zone && (
          <span className="fault-tree-zone">
            Selected zone: {selected.zone}
          </span>
        )}
      </div>
      <div className="fault-tree-top">
        <span>Event to investigate</span>
        <strong>
          Dispatch-to-arrival time exceeds {targetLabel}
          {Number.isFinite(threshold) ? " minutes" : ""}
        </strong>
      </div>
      <div className="fault-tree-gate">
        <strong>Possible paths</strong>
        <span>
          Factors can contribute alone or together; investigate the evidence.
        </span>
      </div>
      <ul className="fault-tree-paths" aria-label="Hypothesized delay paths">
        {paths.map((path) => (
          <li key={path.title}>
            <h4>{path.title}</h4>
            <p className="fault-tree-question">{path.question}</p>
            <p>{path.examples}</p>
          </li>
        ))}
      </ul>
      <div className="fault-tree-footer">
        <p>
          {context && (
            <>
              <strong>
                {context.late_reason_recorded_count} of {context.late_count}
              </strong>{" "}
              above-target completed calls in {selected.zone} have a recorded
              reason, across all observed periods.{" "}
            </>
          )}
          Recorded reasons can help prioritize checks; they do not verify these
          paths. The current data does not measure each step separately, so this
          tree has no estimated probabilities. This starting map is not
          exhaustive: combined factors, other delays, or timestamp errors may
          explain an exceedance. A branch alone does not prove that the target
          will be exceeded.
        </p>
        {onOpenInsights && (
          <button type="button" onClick={onOpenInsights}>
            Inspect delay context <span aria-hidden="true">→</span>
          </button>
        )}
      </div>
    </section>
  );
}

export default StatisticsGuide;
