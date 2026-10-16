import React, { useState } from "react";
const pct = (x) => (x == null ? "Not available" : `${(x * 100).toFixed(1)}%`);
export default function DelayPatterns({ overall, selected, zone }) {
  const [scope, setScope] = useState("zone");
  const data = scope === "all" ? overall : selected;
  if (!data) return null;
  const max = Math.max(1, ...data.reasons.map((r) => r.late_count));
  return (
    <section className="panel delay-patterns">
      <div className="panel-heading">
        <div>
          <h3>Delay patterns · investigation context</h3>
          <p>
            Selected priority · all observed periods · logged associations are
            not causes.
          </p>
        </div>
        <label className="scope-label">
          Scope
          <select
            aria-label="Delay patterns scope"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
          >
            <option value="zone">{zone}</option>
            <option value="all">All zones</option>
          </select>
        </label>
      </div>
      <div className="context-coverage">
        <span>
          <strong>{pct(data.reason_coverage)}</strong> of {data.count} calls
          have a recorded reason ({data.reason_recorded_count})
        </span>
        <span>
          <strong>{pct(data.late_reason_coverage)}</strong> of {data.late_count}{" "}
          above-target calls have a recorded reason (
          {data.late_reason_recorded_count})
        </span>
      </div>
      <div className="context-section">
        <h4>Above-target calls by logged reason</h4>
        <p>
          Descending count (Pareto order). Cumulative percentages use all
          above-target calls, including “Not recorded”. A logged reason may
          reflect reporting habits as well as operational conditions.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Logged reason</th>
                <th>Above-target calls</th>
                <th>All calls with reason</th>
                <th>Share of above-target</th>
                <th>Cumulative share</th>
              </tr>
            </thead>
            <tbody>
              {data.reasons.map((r) => (
                <tr key={r.reason}>
                  <td>{r.reason}</td>
                  <td>
                    <div className="pareto-count">
                      <span
                        className="pareto-bar"
                        style={{ width: `${(100 * r.late_count) / max}%` }}
                      />
                      <strong>{r.late_count}</strong>
                    </div>
                  </td>
                  <td>{r.count}</td>
                  <td>{pct(r.late_share)}</td>
                  <td>{pct(r.cumulative_late_share)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="context-section">
        <h4>Compare observable field conditions</h4>
        <p>
          Wilson 95% intervals describe each group's above-target proportion.
          These unadjusted groups can differ in zone, workload, priority and
          time; do not rank causes or interpret overlap as a significance test.
        </p>
        {data.strata.map((s) => (
          <details className="context-stratum" key={s.field} open>
            <summary>
              {s.label} <span>{s.missing_count} calls not recorded</span>
            </summary>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{s.label}</th>
                    <th>Calls (n)</th>
                    <th>Above target (n)</th>
                    <th>Above target</th>
                    <th>95% Wilson interval</th>
                    <th>p90 minutes</th>
                  </tr>
                </thead>
                <tbody>
                  {s.groups.map((g) => (
                    <tr key={g.value}>
                      <td>{g.value}</td>
                      <td>{g.count}</td>
                      <td>{g.late_count}</td>
                      <td>{pct(g.late_rate)}</td>
                      <td>
                        {pct(g.late_ci_low)} – {pct(g.late_ci_high)}
                      </td>
                      <td>
                        {g.p90_minutes == null ? "—" : g.p90_minutes.toFixed(1)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        ))}
      </div>
      <div className="investigate">
        {data.warning} Missing context is shown explicitly and never assumed to
        mean no delay.
      </div>
    </section>
  );
}
