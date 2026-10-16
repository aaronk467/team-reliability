import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowUpRight,
  Check,
  ChevronDown,
  Clock3,
  Download,
  FileText,
  LayoutDashboard,
  MapPin,
  Plus,
  Radio,
  ShieldCheck,
  Upload,
  X,
  AlertTriangle,
} from "lucide-react";
import "./style.css";
const columns = [
  "id",
  "zone",
  "priority",
  "dispatched_at",
  "arrived_at",
  "delay_reason",
];
const fmt = (x, d = 1) => (x == null ? "—" : Number(x).toFixed(d));
const pct = (x) => (x == null ? "—" : `${(x * 100).toFixed(1)}%`);
function parseCSV(text) {
  const rows = [];
  let row = [],
    cell = "",
    quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') {
        cell += '"';
        i++;
      } else quoted = !quoted;
    } else if (c === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((c === "\n" || c === "\r") && !quoted) {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      if (row.some((x) => x.trim())) rows.push(row);
      row = [];
      cell = "";
    } else cell += c;
  }
  if (quoted) throw Error("CSV contains an unclosed quoted field.");
  row.push(cell);
  if (row.some((x) => x.trim())) rows.push(row);
  const header = rows.shift()?.map((x) => x.trim().replace(/^\uFEFF/, ""));
  if (!header || columns.slice(0, 5).some((c) => !header.includes(c)))
    throw Error(
      "CSV needs id, zone, priority, dispatched_at and arrived_at columns.",
    );
  return rows.map((r, i) => {
    if (r.length !== header.length)
      throw Error(`CSV row ${i + 2} has an unexpected number of fields.`);
    return Object.fromEntries(header.map((h, j) => [h, r[j]]));
  });
}
function Chart({
  title,
  subtitle,
  points,
  value,
  center,
  lower,
  upper,
  target,
  percent = false,
}) {
  const W = 850,
    H = 210,
    pad = { l: 45, r: 20, t: 20, b: 30 };
  const all = points
    .flatMap((p) => [
      p[value],
      typeof upper === "string" ? p[upper] : upper,
      target,
    ])
    .filter((x) => x != null && Number.isFinite(x));
  const max = percent ? 1 : Math.max(1, ...all) * 1.12;
  const X = (i) =>
      pad.l + (i * (W - pad.l - pad.r)) / Math.max(1, points.length - 1),
    Y = (v) => H - pad.b - (v / max) * (H - pad.t - pad.b);
  const line = (key) =>
    points
      .map((p, i) => `${X(i)},${Y(typeof key === "string" ? p[key] : key)}`)
      .join(" ");
  const tick = (x) => (percent ? `${Math.round(x * 100)}%` : fmt(x, 0));
  const boundary = points.findIndex((p) => !p.in_baseline);
  return (
    <section className="panel chart-panel">
      <div className="panel-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <span className="small-badge">3σ limits</span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${title}, baseline center and three sigma control limits`}
      >
        <rect
          x={pad.l}
          y={pad.t}
          width={
            boundary > 0
              ? X(boundary) - pad.l
              : boundary === -1
                ? W - pad.l - pad.r
                : 0
          }
          height={H - pad.t - pad.b}
          fill="#f0f5fa"
        />
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line
              x1={pad.l}
              x2={W - pad.r}
              y1={Y(max * t)}
              y2={Y(max * t)}
              stroke="#e7edf3"
            />
            <text
              x={pad.l - 8}
              y={Y(max * t) + 4}
              textAnchor="end"
              className="axis"
            >
              {tick(max * t)}
            </text>
          </g>
        ))}
        {[lower, upper].map(
          (v, i) =>
            v != null &&
            points.every((p) => typeof v !== "string" || p[v] != null) && (
              <polyline
                key={i}
                points={line(v)}
                fill="none"
                stroke="#b68a4a"
                strokeWidth="1.5"
                strokeDasharray="5 5"
              />
            ),
        )}
        {center != null && (
          <line
            x1={pad.l}
            x2={W - pad.r}
            y1={Y(center)}
            y2={Y(center)}
            stroke="#698da1"
            strokeDasharray="3 4"
          />
        )}
        {target != null && (
          <line
            x1={pad.l}
            x2={W - pad.r}
            y1={Y(target)}
            y2={Y(target)}
            stroke="#a882cf"
            strokeDasharray="8 4"
          />
        )}
        <polyline
          points={line(value)}
          fill="none"
          stroke="#1682a1"
          strokeWidth="1.7"
        />
        {points.map((p, i) => (
          <circle
            key={i}
            cx={X(i)}
            cy={Y(p[value])}
            r={p.signal ? 3.5 : 2}
            fill={p.signal ? "#dc6a48" : "#1682a1"}
          >
            <title>
              {p.date || p.dispatched_at}: {fmt(p[value], 2)}
              {p.signal ? " — outside control limits" : ""}
              {p.n ? `; n=${p.n}` : ""}
            </title>
          </circle>
        ))}
        <text x={pad.l} y={H - 6} className="axis">
          {points[0]?.date || points[0]?.dispatched_at?.slice(0, 10)}
        </text>
        <text x={W - pad.r} y={H - 6} textAnchor="end" className="axis">
          {points.at(-1)?.date || points.at(-1)?.dispatched_at?.slice(0, 10)}
        </text>
      </svg>
      <div className="legend">
        <span>
          <i className="dot blue" /> Observations
        </span>
        <span>
          <i className="dot orange" /> Outside limits
        </span>
        <span>– – Control limits</span>
        <span>··· Baseline center {percent ? pct(center) : fmt(center)}</span>
        {target != null && (
          <span className="purple">– – Service target {target} min</span>
        )}
        <span className="baseline-key">Shaded: baseline</span>
      </div>
    </section>
  );
}
function App() {
  const [datasets, setDatasets] = useState([]),
    [dataset, setDataset] = useState(""),
    [records, setRecords] = useState([]),
    [result, setResult] = useState(null),
    [zone, setZone] = useState(""),
    [target, setTarget] = useState(8),
    [baseline, setBaseline] = useState(20),
    [priority, setPriority] = useState("all"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [modal, setModal] = useState(false),
    [tab, setTab] = useState("overview"),
    [source, setSource] = useState(""),
    [notice, setNotice] = useState("");
  async function request(url, options) {
    const r = await fetch(url, options);
    const data = await r.json();
    if (!r.ok)
      throw Error(
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail || data),
      );
    return data;
  }
  useEffect(() => {
    request("/api/datasets")
      .then((data) => {
        const list = Array.isArray(data) ? data : data.datasets;
        setDatasets(list);
        if (list.length) {
          const preferred =
            list.find(
              (d) => (typeof d === "string" ? d : d.name) === "south_shift",
            ) || list[0];
          setDataset(
            typeof preferred === "string" ? preferred : preferred.name,
          );
        }
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (!dataset) return;
    setBusy(true);
    setError("");
    request(`/api/datasets/${dataset}`)
      .then((data) => {
        const base = Array.isArray(data) ? data : data.records;
        let extra = [];
        try {
          extra = JSON.parse(
            localStorage.getItem(`responsewatch:${dataset}`) || "[]",
          );
        } catch {}
        setRecords([...base, ...extra]);
        setSource(dataset);
        setNotice(
          extra.length
            ? `${extra.length} browser-saved call(s) added to this demo.`
            : "",
        );
      })
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }, [dataset]);
  useEffect(() => {
    if (!records.length) return;
    let cancelled = false;
    setBusy(true);
    setError("");
    request("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        records,
        target_minutes: Number(target),
        baseline_days: Number(baseline),
        priority,
      }),
    })
      .then((data) => {
        if (cancelled) return;
        setResult(data);
        setZone((z) =>
          data.zones.some((x) => x.zone === z) ? z : data.zones[0]?.zone,
        );
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message);
          setResult(null);
        }
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [records, target, baseline, priority]);
  const selected = result?.zones.find((z) => z.zone === zone);
  const alerts =
    selected?.imr.points.filter(
      (p) => !p.in_baseline && (p.signal || p.mr_signal),
    ) || [];
  const summary = result?.summary;
  function exportCSV() {
    const text = [
      columns.join(","),
      ...records.map((r) =>
        columns
          .map((c) => '"' + String(r[c] ?? "").replaceAll('"', '""') + '"')
          .join(","),
      ),
    ].join("\n");
    const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "responsewatch-dispatches.csv";
    a.click();
    URL.revokeObjectURL(url);
  }
  async function upload(e) {
    try {
      const f = e.target.files[0];
      if (!f) return;
      const rows = parseCSV(await f.text());
      if (!rows.length) throw Error("CSV has no records.");
      setRecords(rows);
      setSource(f.name);
      setNotice(
        "Uploaded data stays in this browser session and is sent to the analysis API.",
      );
      setError("");
    } catch (err) {
      setError(err.message);
    }
    e.target.value = "";
  }
  async function saveCall(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const row = Object.fromEntries(form);
    try {
      row.dispatched_at = new Date(row.dispatched_at).toISOString();
      row.arrived_at = new Date(row.arrived_at).toISOString();
      if (new Date(row.arrived_at) < new Date(row.dispatched_at))
        throw Error("Arrival must follow dispatch.");
      if (records.some((r) => r.id === row.id))
        throw Error("Call ID must be unique.");
      await request("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          records: [...records, row],
          target_minutes: Number(target),
          baseline_days: Number(baseline),
          priority,
        }),
      });
      if (source === dataset) {
        const key = `responsewatch:${dataset}`;
        const saved = JSON.parse(localStorage.getItem(key) || "[]");
        localStorage.setItem(key, JSON.stringify([...saved, row]));
      }
      setRecords([...records, row]);
      setModal(false);
      setNotice(
        "Completed call added. Demo additions are stored in this browser, not a production dispatch database.",
      );
    } catch (err) {
      setError(err.message);
    }
  }
  return (
    <div className="app">
      <aside>
        <a className="brand" href="#">
          <span className="brand-icon">
            <Activity size={25} />
          </span>
          <span>
            Response<span className="brand-light">Watch</span>
            <small>EMERGENCY RESPONSE INTELLIGENCE</small>
          </span>
        </a>
        <div className="workspace">
          <span className="workspace-avatar">MR</span>
          <div>
            Metro Response<small>Quality & reliability workspace</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <p className="nav-label">WORKSPACE</p>
        <button
          className={tab === "overview" ? "nav-item active" : "nav-item"}
          onClick={() => setTab("overview")}
        >
          <LayoutDashboard size={18} /> Reliability overview
        </button>
        <button
          className={tab === "log" ? "nav-item active" : "nav-item"}
          onClick={() => setTab("log")}
        >
          <Radio size={18} /> Dispatch log{" "}
          <span className="nav-count">{records.length}</span>
        </button>
        <button
          className={tab === "methods" ? "nav-item active" : "nav-item"}
          onClick={() => setTab("methods")}
        >
          <FileText size={18} /> Methods & guidance
        </button>
        <div className="sidebar-bottom">
          <ShieldCheck size={21} />
          <strong>Better signals. Better response.</strong>
          <p>Make variation visible before it becomes the monthly average.</p>
          <span>
            <i /> ANALYSIS WORKSPACE
          </span>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Workspace <span>/</span>{" "}
            {tab === "overview"
              ? "Reliability overview"
              : tab === "log"
                ? "Dispatch log"
                : "Methods & guidance"}
          </div>
          <div className="header-right">
            <span className="demo-dot" /> Demonstration environment{" "}
            <span className="avatar">QC</span>
          </div>
        </header>
        <div className="content">
          <div className="title-row">
            <div>
              <div className="eyebrow">DISPATCH PERFORMANCE</div>
              <h1>
                {tab === "overview"
                  ? "Every minute matters."
                  : tab === "log"
                    ? "A clear record of every response."
                    : "Understand the signals."}
              </h1>
              <p>
                Monitor response-time variation, spot unusual patterns, and
                focus your next investigation.
              </p>
            </div>
            <button className="primary" onClick={() => setModal(true)}>
              <Plus size={17} /> Log completed call
            </button>
          </div>
          <div className="controls panel">
            <div className="control source-control">
              <label htmlFor="dataset">Demonstration dataset</label>
              <select
                id="dataset"
                value={dataset}
                onChange={(e) => setDataset(e.target.value)}
              >
                {datasets.map((d) => {
                  const name = typeof d === "string" ? d : d.name;
                  return (
                    <option key={name} value={name}>
                      {typeof d === "string"
                        ? d.replaceAll("_", " ")
                        : d.title || d.label || name.replaceAll("_", " ")}
                    </option>
                  );
                })}
              </select>
            </div>
            <div className="control">
              <label htmlFor="target">Service target (min)</label>
              <input
                id="target"
                type="number"
                min="0.1"
                max="180"
                step="0.5"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              />
            </div>
            <div className="control">
              <label htmlFor="baseline">Baseline (first UTC days)</label>
              <input
                id="baseline"
                type="number"
                min="1"
                max="3650"
                value={baseline}
                onChange={(e) => setBaseline(e.target.value)}
              />
            </div>
            <div className="control">
              <label htmlFor="priority">Priority</label>
              <select
                id="priority"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
              >
                <option value="all">All priorities</option>
                <option value="high">High</option>
                <option value="standard">Standard</option>
              </select>
            </div>
            <div className="control-actions">
              <label className="icon-button upload" title="Upload CSV">
                <Upload size={17} />
                <span>Upload CSV</span>
                <input type="file" accept=".csv,text/csv" onChange={upload} />
              </label>
              <button
                className="icon-button"
                onClick={exportCSV}
                disabled={!records.length}
                title="Export records"
              >
                <Download size={17} />
              </button>
            </div>
          </div>
          <div className="data-meta">
            <span>
              <i />{" "}
              {busy
                ? "Updating analysis…"
                : `${source || "Loading dataset"} · ${records.length.toLocaleString()} completed calls`}
            </span>
            {result && (
              <span>
                Baseline {result.baseline_start} – {result.baseline_end} · UTC
              </span>
            )}
          </div>
          {error && (
            <div className="error" role="alert">
              <AlertTriangle size={18} />
              {error}
            </div>
          )}
          {notice && <div className="notice">{notice}</div>}
          {tab === "overview" && (
            <>
              {summary && (
                <div className="metrics">
                  <Metric
                    label="COMPLETED RESPONSES"
                    value={summary.count.toLocaleString()}
                    detail="Observed calls · selected priority"
                    icon={<Radio />}
                  />
                  <Metric
                    label="90TH PERCENTILE"
                    value={
                      <>
                        {fmt(summary.p90_minutes)} <small>min</small>
                      </>
                    }
                    detail="90% of observed responses at or below"
                    icon={<Clock3 />}
                  />
                  <Metric
                    label="ABOVE SERVICE TARGET"
                    value={pct(summary.late_rate)}
                    detail={`${summary.late_count} calls took more than ${target} minutes`}
                    icon={<AlertTriangle />}
                    warning
                  />
                  <Metric
                    label="95% CONFIDENCE INTERVAL"
                    value={`${pct(summary.late_ci_low)}–${pct(summary.late_ci_high)}`}
                    detail="Wilson interval · above-target proportion"
                    icon={<ShieldCheck />}
                  />
                </div>
              )}
              <div className="section-heading">
                <div>
                  <h2>Where to focus</h2>
                  <p>
                    Compare zones, then inspect the process behind the numbers.
                  </p>
                </div>
                <span className="small-badge">
                  {result?.zones.length || 0} zones monitored
                </span>
              </div>
              <div className="zones">
                {result?.zones.map((z) => {
                  const n = z.imr.points.filter(
                    (p) => !p.in_baseline && (p.signal || p.mr_signal),
                  ).length;
                  return (
                    <button
                      key={z.zone}
                      onClick={() => setZone(z.zone)}
                      className={`zone-card ${zone === z.zone ? "selected" : ""}`}
                    >
                      <div className="zone-title">
                        <span>
                          <MapPin size={16} /> {z.zone}
                        </span>
                        <ArrowUpRight size={17} />
                      </div>
                      <strong>
                        {pct(z.late_rate)}
                        <small> above target</small>
                      </strong>
                      <div className="zone-footer">
                        <span>
                          {
                            z.p_chart.points.filter(
                              (p) => !p.in_baseline && p.signal,
                            ).length
                          }{" "}
                          daily p signals · {z.count} calls · p90{" "}
                          {fmt(z.p90_minutes)}m
                        </span>
                        <span className={n ? "signal-tag" : "stable-tag"}>
                          {n
                            ? `${n} I-MR signal${n === 1 ? "" : "s"}`
                            : "No I-MR signals"}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
              {selected && (
                <>
                  <div className="section-heading chart-heading">
                    <div>
                      <h2>
                        {selected.zone}{" "}
                        <span className="heading-light">
                          / Process monitoring
                        </span>
                      </h2>
                      <p>
                        Frozen baseline limits distinguish routine variation
                        from unusual observations.
                      </p>
                    </div>
                    <span className="small-badge">
                      {selected.baseline_count} baseline calls
                    </span>
                  </div>
                  {selected.warnings.map((w) => (
                    <div className="warning" key={w}>
                      <AlertTriangle size={15} />
                      {w}
                    </div>
                  ))}
                  <Chart
                    title="Individual response times"
                    subtitle="Dispatch to on-scene · minutes · chronological calls"
                    points={selected.imr.points}
                    value="minutes"
                    center={selected.imr.center}
                    lower={selected.imr.lcl}
                    upper={selected.imr.ucl}
                    target={Number(target)}
                  />
                  <div className="chart-grid">
                    <Chart
                      title="Moving range"
                      subtitle="Absolute difference between consecutive calls · minutes"
                      points={selected.imr.points
                        .filter((p) => p.moving_range != null)
                        .map((p) => ({ ...p, signal: p.mr_signal }))}
                      value="moving_range"
                      center={selected.imr.mr_center}
                      lower={0}
                      upper={selected.imr.mr_ucl}
                    />
                    <Chart
                      title="Daily above-target proportion"
                      subtitle="p chart · limits adapt to observed daily call volume"
                      points={selected.p_chart.points}
                      value="proportion"
                      center={selected.p_chart.center}
                      lower="lcl"
                      upper="ucl"
                      percent
                    />
                  </div>
                  <section className="panel daily-signals">
                    <div className="panel-heading">
                      <div>
                        <h3>Daily proportion signals</h3>
                        <p>
                          Monitoring days outside p-chart limits; inspect daily
                          denominators and call mix.
                        </p>
                      </div>
                    </div>
                    {selected.p_chart.points.some(
                      (p) => !p.in_baseline && p.signal,
                    ) ? (
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>UTC day</th>
                              <th>Calls (n)</th>
                              <th>Above target</th>
                              <th>Proportion</th>
                              <th>Control limits</th>
                              <th>Direction</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selected.p_chart.points
                              .filter((p) => !p.in_baseline && p.signal)
                              .map((p) => (
                                <tr key={p.date}>
                                  <td>{p.date}</td>
                                  <td>{p.n}</td>
                                  <td>{p.late_count}</td>
                                  <td>{pct(p.proportion)}</td>
                                  <td>
                                    {pct(p.lcl)} – {pct(p.ucl)}
                                  </td>
                                  <td>
                                    {p.proportion > p.ucl
                                      ? "Higher than baseline limits"
                                      : "Lower than baseline limits"}
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="empty">
                        <strong>
                          No monitoring-period daily p-chart signals
                        </strong>
                        <p>
                          Absence of signals does not imply the service target
                          is met.
                        </p>
                      </div>
                    )}
                  </section>
                  <section className="panel signals">
                    <div className="panel-heading">
                      <div>
                        <h3>Investigation queue</h3>
                        <p>
                          Monitoring-period I-MR signals · unusual observations
                          are clues, not confirmed causes.
                        </p>
                      </div>
                      <span className="small-badge">{alerts.length} calls</span>
                    </div>
                    {alerts.length ? (
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>Call ID</th>
                              <th>Dispatch (UTC)</th>
                              <th>Response</th>
                              <th>Signal</th>
                              <th>Logged context</th>
                            </tr>
                          </thead>
                          <tbody>
                            {alerts.slice(0, 30).map((p) => (
                              <tr key={p.id}>
                                <td className="mono">{p.id}</td>
                                <td>
                                  {p.dispatched_at
                                    .replace("T", " ")
                                    .slice(0, 16)}
                                </td>
                                <td>{fmt(p.minutes)} min</td>
                                <td>
                                  <span className="signal-tag">
                                    {p.signal
                                      ? "Individual outside limits"
                                      : "Moving range outside limits"}
                                  </span>
                                </td>
                                <td>
                                  {records.find((r) => r.id === p.id)
                                    ?.delay_reason || "Not recorded"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {alerts.length > 30 && (
                          <p className="table-note">
                            Showing first 30 signals. Export records for a full
                            review.
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="empty">
                        <Check size={22} />
                        <strong>No monitoring-period I-MR signals</strong>
                        <p>
                          Review the daily p chart and service-target
                          performance alongside these limits.
                        </p>
                      </div>
                    )}
                    <div className="investigate">
                      <strong>Next step</strong> Check timestamp accuracy,
                      staffing and vehicle availability, route conditions, and
                      case mix. A low-side signal can suggest improvement;
                      validate it before changing the baseline.
                    </div>
                  </section>
                </>
              )}
              <div className="footnote">
                <ShieldCheck size={16} />
                <p>
                  {result?.warnings?.join(" ") ||
                    "Load a dataset to begin. Synthetic demonstrations do not establish a clinical standard."}{" "}
                  The service target is a configurable planning threshold, not a
                  clinical guarantee.
                </p>
              </div>
            </>
          )}
          {tab === "log" && (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h3>Completed dispatch records</h3>
                  <p>
                    No patient details. Timestamps include timezone offsets;
                    analysis uses UTC.
                  </p>
                </div>
                <button className="secondary" onClick={exportCSV}>
                  <Download size={15} /> Export CSV
                </button>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      {[
                        "Call ID",
                        "Zone",
                        "Priority",
                        "Dispatched",
                        "Arrived",
                        "Delay context",
                      ].map((t) => (
                        <th key={t}>{t}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {records
                      .slice(-100)
                      .reverse()
                      .map((r) => (
                        <tr key={r.id}>
                          <td className="mono">{r.id}</td>
                          <td>{r.zone}</td>
                          <td>{r.priority}</td>
                          <td>{r.dispatched_at}</td>
                          <td>{r.arrived_at}</td>
                          <td>{r.delay_reason || "Not recorded"}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
              <p className="table-note">
                Showing latest 100 of {records.length} records. All records are
                included in analysis. Logging here is a local demonstration, not
                a live 911 integration.
              </p>
            </section>
          )}
          {tab === "methods" && (
            <section className="panel methods">
              <h2>Statistics before averages</h2>
              <p>
                ResponseWatch helps dispatch supervisors investigate variation
                in dispatch-to-on-scene times. It analyzes completed responses
                only; missing arrivals and canceled calls need a separate
                operational review.
              </p>
              <h3>Individual and moving-range charts</h3>
              <p>
                Calls are ordered by dispatch time within each zone. The first
                configured UTC calendar days form a frozen baseline. The
                individual center is the baseline mean, and limits are mean ± 3
                × mean moving range / 1.128 (lower limit clipped at zero). The
                moving-range upper limit is 3.267 × baseline mean moving range.
                A point strictly outside a limit is flagged; other run rules are
                not applied.
              </p>
              <h3>Daily p chart and uncertainty</h3>
              <p>
                A response is above target only when its duration is strictly
                greater than your threshold. The p-chart center is the pooled
                baseline above-target proportion. Limits use each observed day's
                call count: p ± 3√(p(1−p)/n), bounded by zero and one. Days
                without calls are omitted. Small expected counts or
                all-on-time/all-late baselines make this approximation
                unreliable. Summary uncertainty uses a 95% Wilson interval.
              </p>
              <h3>Use these signals carefully</h3>
              <p>
                Response times can be skewed, serially correlated, and sensitive
                to priority and case mix. Inspect these assumptions and stratify
                priority before interpreting limits. Baselines should represent
                a consistent process. Limits describe observed variation; they
                are separate from service targets. Signals do not identify
                causes or demonstrate patient outcomes.
              </p>
              <h3>Field collection</h3>
              <p>
                Capture a nonpatient call ID, operational zone, priority at
                dispatch, timezone-aware dispatch and on-scene timestamps, and
                an optional standardized delay reason. Synchronize clocks and
                audit missing arrivals, duplicate IDs, and timestamp edits. See
                the repository dataset codebook for the full collection
                protocol.
              </p>
            </section>
          )}
          <footer>
            ResponseWatch{" "}
            <span>
              Quality control for emergency response · Synthetic demonstration
              data
            </span>
            <a href="/docs" target="_blank" rel="noreferrer">
              API documentation <ArrowUpRight size={12} />
            </a>
          </footer>
        </div>
      </main>
      {modal && (
        <div className="modal-backdrop">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <button
              className="close"
              onClick={() => setModal(false)}
              aria-label="Close"
            >
              <X />
            </button>
            <h2 id="modal-title">Log a completed response</h2>
            <p>
              Browser-local demo only. Do not enter patient or personal
              information.
            </p>
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            <form onSubmit={saveCall}>
              <label>
                Call ID
                <input name="id" required placeholder="CALL-0001" />
              </label>
              <div className="form-grid">
                <label>
                  Zone
                  <input name="zone" required list="zone-list" />
                  <datalist id="zone-list">
                    {result?.zones.map((z) => (
                      <option key={z.zone}>{z.zone}</option>
                    ))}
                  </datalist>
                </label>
                <label>
                  Priority
                  <select name="priority">
                    <option value="high">High</option>
                    <option value="standard">Standard</option>
                  </select>
                </label>
              </div>
              <label>
                Dispatched at (your browser's local time)
                <input
                  name="dispatched_at"
                  required
                  type="datetime-local"
                  step="1"
                />
              </label>
              <label>
                Arrived on scene (your browser's local time)
                <input
                  name="arrived_at"
                  required
                  type="datetime-local"
                  step="1"
                />
              </label>
              <label>
                Delay context (optional)
                <input
                  name="delay_reason"
                  placeholder="e.g. traffic; unknown"
                />
              </label>
              <button className="primary" type="submit">
                <Plus size={16} /> Add completed call
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
function Metric({ label, value, detail, icon, warning }) {
  return (
    <div className={`metric panel ${warning ? "metric-warm" : ""}`}>
      <div className="metric-label">
        {label}
        <span>{icon}</span>
      </div>
      <strong>{value || "—"}</strong>
      <p>{detail}</p>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
