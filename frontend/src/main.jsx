import ResolutionReviews from "./ResolutionReviews";
import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowUpRight,
  Check,
  ChevronDown,
  Clock3,
  Download,
  FileText,
  Info,
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
import OpenCalls from "./OpenCalls";
import DelayPatterns from "./DelayPatterns";
import { StatisticsGuide, FaultTreeGuide } from "./OverviewGuide";
import CallInspection from "./CallInspection";
import AboutPage from "./AboutPage";
import "./Workspace.css";
const workspaceTabs = [
  {
    id: "overview",
    label: "Key statistics",
    icon: LayoutDashboard,
    description:
      "Understand performance, compare zones, and recognize unusual changes.",
  },
  {
    id: "operations",
    label: "Dispatch workspace",
    icon: Radio,
    description:
      "Record responses, inspect a completed call, and organize follow-up.",
  },
  {
    id: "insights",
    label: "Supporting analysis",
    icon: Activity,
    description:
      "Explore delay context, uncertainty, and the detail behind the signals.",
  },
];
function readTab() {
  const id = window.location.hash.slice(1);
  return [...workspaceTabs.map((item) => item.id), "methods", "about"].includes(
    id,
  )
    ? id
    : "overview";
}
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
  if (header.some((h) => !h) || new Set(header).size !== header.length)
    throw Error(
      "CSV headers must be nonempty and unique; no columns were imported.",
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
  exact = false,
  centerLabel = "Baseline center",
  limitLabel,
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
  const tick = (x) =>
    percent ? `${Math.round(x * 100)}%` : fmt(x, max < 3 ? 2 : 0);
  const boundary = points.findIndex((p) => !p.in_baseline);
  return (
    <section className="panel chart-panel">
      <div className="panel-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <span className="small-badge">
          {limitLabel || (exact ? "Exact binomial limits" : "3σ limits")}
        </span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${title}, baseline center and ${limitLabel || (exact ? "exact binomial" : "three sigma")} control limits`}
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
        <span>
          ··· {centerLabel} {percent ? pct(center) : fmt(center)}
        </span>
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
    [priority, setPriority] = useState("high"),
    [scale, setScale] = useState("log"),
    [aggregation, setAggregation] = useState(7),
    [pMethod, setPMethod] = useState("beta_binomial"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [modal, setModal] = useState(false),
    [tab, setTab] = useState(readTab),
    [source, setSource] = useState(""),
    [notice, setNotice] = useState("");
  function navigateTab(next) {
    setTab(next);
    window.history.replaceState(null, "", `#${next}`);
    requestAnimationFrame(() => {
      const destination = document.getElementById(
        next === "methods"
          ? "methods-title"
          : next === "about"
            ? "about-title"
            : `tab-${next}`,
      );
      destination?.focus({ preventScroll: true });
      destination?.scrollIntoView({ block: "nearest" });
    });
  }
  useEffect(() => {
    const update = () => setTab(readTab());
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  function tabKeyDown(event, index) {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % workspaceTabs.length;
    if (event.key === "ArrowLeft")
      next = (index + workspaceTabs.length - 1) % workspaceTabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = workspaceTabs.length - 1;
    if (next == null) return;
    event.preventDefault();
    navigateTab(workspaceTabs[next].id);
    document.getElementById(`tab-${workspaceTabs[next].id}`)?.focus();
  }
  const current = useRef({ source, records, dataset });
  current.current = { source, records, dataset };
  const sourceLoading = useRef(false);
  function assertUnchanged(snapshot) {
    if (
      sourceLoading.current ||
      current.current.source !== snapshot.source ||
      current.current.records !== snapshot.records ||
      current.current.dataset !== snapshot.dataset
    )
      throw Error(
        "The selected source or records changed during validation. Nothing was saved; please retry.",
      );
  }
  function pendingRows(name) {
    const rows = JSON.parse(
      localStorage.getItem(`responsewatch:pending:${name}`) || "[]",
    );
    if (
      !Array.isArray(rows) ||
      rows.some((r) => !r || typeof r.id !== "string")
    )
      throw Error(
        "Saved open-call data is invalid; data preserved. Resolve it in Open dispatches before logging a completed call.",
      );
    return rows;
  }
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
    let cancelled = false;
    sourceLoading.current = true;
    setBusy(true);
    setError("");
    request(`/api/datasets/${dataset}`)
      .then((data) => {
        if (cancelled) return;
        const base = Array.isArray(data) ? data : data.records;
        let extra = [];
        try {
          extra = JSON.parse(
            localStorage.getItem(`responsewatch:${dataset}`) || "[]",
          );
        } catch (e) {
          throw Error(
            `Saved completed records cannot be read; data preserved. ${e.message}`,
          );
        }
        if (!Array.isArray(extra))
          throw Error(
            "Saved completed records must be an array; data preserved.",
          );
        setRecords([...base, ...extra]);
        setSource(dataset);
        setNotice(
          extra.length
            ? `${extra.length} browser-saved call(s) added to this demo.`
            : "",
        );
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) {
          sourceLoading.current = false;
          setBusy(false);
        }
      });
    return () => {
      cancelled = true;
    };
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
        imr_scale: scale,
        aggregation_days: Number(aggregation),
        p_method: pMethod,
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
  }, [records, target, baseline, priority, scale, aggregation, pMethod]);
  const selected = result?.zones.find((z) => z.zone === zone);
  const alerts =
    selected?.imr.points.filter(
      (p) => !p.in_baseline && (p.signal || p.mr_signal),
    ) || [];
  const summary = result?.summary;
  function exportCSV() {
    const headers = [
      ...columns,
      ...new Set(
        records
          .flatMap((r) => Object.keys(r))
          .filter((k) => !columns.includes(k) && !k.startsWith("_")),
      ),
    ];
    const quote = (value) =>
      '"' + String(value ?? "").replaceAll('"', '""') + '"';
    const text = [
      headers.map(quote).join(","),
      ...records.map((r) =>
        headers
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
      const saved = JSON.parse(
        localStorage.getItem(`responsewatch:${f.name}`) || "[]",
      );
      if (!Array.isArray(saved))
        throw Error(
          "Saved uploaded-source records are invalid; data preserved.",
        );
      setRecords([...rows, ...saved]);
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
  async function completeOpen(row, removePending) {
    const snapshot = { source, records, dataset };
    assertUnchanged(snapshot);
    row = { ...row, id: row.id.trim(), zone: row.zone.trim() };
    if (records.some((r) => r.id.trim() === row.id))
      throw Error("Call ID already exists in completed records.");
    await request("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        records: [...records, row],
        target_minutes: Number(target),
        baseline_days: Number(baseline),
        priority,
        imr_scale: scale,
        aggregation_days: Number(aggregation),
        p_method: pMethod,
      }),
    });
    assertUnchanged(snapshot);
    const key = `responsewatch:${snapshot.source}`;
    const saved = JSON.parse(localStorage.getItem(key) || "[]");
    if (!Array.isArray(saved))
      throw Error("Saved completed-call data is invalid; data preserved.");
    localStorage.setItem(key, JSON.stringify([...saved, row]));
    try {
      removePending();
    } catch (e) {
      localStorage.setItem(key, JSON.stringify(saved));
      throw e;
    }
    current.current = { ...current.current, records: [...records, row] };
    setRecords(current.current.records);
    setNotice(
      "Arrival validated and added to completed analysis. This is a browser-local demonstration.",
    );
  }
  async function saveCall(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const row = Object.fromEntries(form);
    const snapshot = { source, records, dataset };
    try {
      assertUnchanged(snapshot);
      row.id = row.id.trim();
      row.zone = row.zone.trim();
      if (pendingRows(source).some((r) => r.id.trim() === row.id))
        throw Error(
          "This ID belongs to an open dispatch. Record its arrival in Open dispatches instead.",
        );
      row.dispatched_at = new Date(row.dispatched_at).toISOString();
      row.arrived_at = new Date(row.arrived_at).toISOString();
      if (new Date(row.arrived_at) < new Date(row.dispatched_at))
        throw Error("Arrival must follow dispatch.");
      if (records.some((r) => r.id.trim() === row.id))
        throw Error("Call ID must be unique.");
      await request("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          records: [...records, row],
          target_minutes: Number(target),
          baseline_days: Number(baseline),
          priority,
          imr_scale: scale,
          aggregation_days: Number(aggregation),
          p_method: pMethod,
        }),
      });
      assertUnchanged(snapshot);
      if (pendingRows(source).some((r) => r.id.trim() === row.id))
        throw Error(
          "An open dispatch now uses this ID. Nothing was saved; record its arrival instead.",
        );
      if (source) {
        const key = `responsewatch:${source}`;
        const saved = JSON.parse(localStorage.getItem(key) || "[]");
        if (!Array.isArray(saved))
          throw Error("Saved completed-call data is invalid; data preserved.");
        localStorage.setItem(key, JSON.stringify([...saved, row]));
      }
      current.current = { ...current.current, records: [...records, row] };
      setRecords(current.current.records);
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
        {workspaceTabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={tab === id ? "nav-item active" : "nav-item"}
            onClick={() => navigateTab(id)}
            aria-current={tab === id ? "page" : undefined}
            title={label}
          >
            <Icon size={18} /> {label}
            {id === "operations" && (
              <span className="nav-count">{records.length}</span>
            )}
          </button>
        ))}
        <button
          className={tab === "methods" ? "nav-item active" : "nav-item"}
          onClick={() => navigateTab("methods")}
          title="Methods & guidance"
        >
          <FileText size={18} /> Methods & guidance
        </button>
        <button
          className={tab === "about" ? "nav-item active" : "nav-item"}
          onClick={() => navigateTab("about")}
          aria-current={tab === "about" ? "page" : undefined}
          title="About"
        >
          <Info size={18} /> About
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
            {workspaceTabs.find((item) => item.id === tab)?.label ||
              (tab === "about" ? "About" : "Methods & guidance")}
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
              <h1
                id={tab === "about" ? "about-title" : undefined}
                tabIndex={tab === "about" ? -1 : undefined}
              >
                {tab === "overview"
                  ? "Understand what matters."
                  : tab === "operations"
                    ? "Track calls. Take action."
                    : tab === "insights"
                      ? "Explore the supporting evidence."
                      : tab === "about"
                        ? "About ResponseWatch"
                        : "Understand the signals."}
              </h1>
              <p>
                {workspaceTabs.find((item) => item.id === tab)?.description ||
                  (tab === "about"
                    ? "Meet the team behind the project."
                    : "Statistical methods, assumptions, and field collection guidance.")}
              </p>
            </div>
            {tab === "operations" && (
              <button
                className="primary"
                onClick={() => setModal(true)}
                aria-label="Log completed call"
              >
                <Plus size={17} /> Log completed call
              </button>
            )}
          </div>
          <div
            className="workspace-tabs"
            role="tablist"
            aria-label="Dashboard sections"
          >
            {workspaceTabs.map(({ id, label, icon: Icon }, index) => (
              <button
                key={id}
                id={"tab-" + id}
                role="tab"
                aria-label={label}
                aria-selected={tab === id}
                aria-controls={"panel-" + id}
                tabIndex={
                  tab === id ||
                  (["methods", "about"].includes(tab) && index === 0)
                    ? 0
                    : -1
                }
                onClick={() => navigateTab(id)}
                onKeyDown={(event) => tabKeyDown(event, index)}
              >
                <Icon size={17} aria-hidden="true" />
                <span>{label}</span>
                <small>{index + 1}</small>
              </button>
            ))}
          </div>
          <div className="controls panel" hidden={tab === "about"}>
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
            <div className="control">
              <label htmlFor="scale">I-MR scale</label>
              <select
                id="scale"
                value={scale}
                onChange={(e) => setScale(e.target.value)}
              >
                <option value="log">Log time (recommended)</option>
                <option value="raw">Raw minutes</option>
              </select>
            </div>
            <div className="control">
              <label htmlFor="aggregation">Proportion chart buckets</label>
              <select
                id="aggregation"
                value={aggregation}
                onChange={(e) => setAggregation(Number(e.target.value))}
              >
                <option value={7}>7 UTC days</option>
                <option value={1}>1 UTC day</option>
              </select>
            </div>
            <div className="control">
              <label htmlFor="p-method">Proportion limits</label>
              <select
                id="p-method"
                value={pMethod}
                onChange={(e) => setPMethod(e.target.value)}
              >
                <option value="beta_binomial">
                  Predictive (baseline uncertainty)
                </option>
                <option value="exact_binomial">
                  Binomial (fixed risk estimate)
                </option>
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
          <div className="data-meta" hidden={tab === "about"}>
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
          {error && tab !== "about" && (
            <div className="error" role="alert">
              <AlertTriangle size={18} />
              {error}
            </div>
          )}
          {notice && tab !== "about" && <div className="notice">{notice}</div>}
          <div className="workspace-context" hidden={tab === "about"}>
            <label htmlFor="focus-zone">Focus zone</label>
            <select
              id="focus-zone"
              value={zone}
              onChange={(e) => setZone(e.target.value)}
              disabled={!result}
            >
              {result?.zones.map((item) => (
                <option key={item.zone} value={item.zone}>
                  {item.zone}
                </option>
              ))}
            </select>
            <span>Dataset, settings, and zone stay the same across tabs.</span>
          </div>
          <section
            id="panel-overview"
            role="tabpanel"
            aria-labelledby="tab-overview"
            hidden={tab !== "overview"}
            tabIndex={0}
          >
            {summary && (
              <div className="metrics primary-metrics">
                <Metric
                  label="COMPLETED RESPONSES"
                  value={summary.count.toLocaleString()}
                  detail="All zones · all periods · selected priority"
                  icon={<Radio />}
                />
                <Metric
                  label="90TH PERCENTILE"
                  value={
                    <>
                      {fmt(summary.p90_minutes)} <small>min</small>
                    </>
                  }
                  detail="All zones · all periods · 90% at or below"
                  icon={<Clock3 />}
                />
                <Metric
                  label="ABOVE SERVICE TARGET"
                  value={pct(summary.late_rate)}
                  detail={`All periods · ${summary.late_count} calls > ${target} min`}
                  icon={<AlertTriangle />}
                  warning
                />
              </div>
            )}
            <StatisticsGuide
              onOpenOperations={() => navigateTab("operations")}
              onOpenInsights={() => navigateTab("insights")}
            />
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
                        period proportion signals · {z.count} calls · p90{" "}
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
                      Frozen baseline limits distinguish routine variation from
                      unusual observations.
                    </p>
                  </div>
                  <span className="small-badge">
                    {selected.baseline_count} baseline calls
                  </span>
                </div>
                {selected.comparison && (
                  <Comparison
                    title={`${selected.zone} · baseline vs monitoring`}
                    data={selected.comparison}
                  />
                )}
                {selected.warnings.map((w) => (
                  <div className="warning" key={w}>
                    <AlertTriangle size={15} />
                    {w}
                  </div>
                ))}
                {selected.baseline_quality?.review_recommended && (
                  <div className="warning baseline-summary">
                    <AlertTriangle size={15} />
                    <span>
                      Review the reference period before acting on its limits.{" "}
                      <button
                        className="text-button"
                        onClick={() => navigateTab("insights")}
                      >
                        See baseline quality
                      </button>
                    </span>
                  </div>
                )}
                <p className="reading-note">
                  Read the target and statistical limits separately. A response
                  can miss the target while staying within the usual variation.
                  Orange points need investigation; lower signals may indicate
                  improvement.
                </p>
                <Chart
                  title="Individual response times"
                  centerLabel={
                    scale === "log"
                      ? "Baseline geometric mean (min)"
                      : "Baseline mean (min)"
                  }
                  subtitle={
                    scale === "log"
                      ? "Log I-MR · center and limits backtransformed to minutes"
                      : "Raw I-MR · dispatch to on-scene minutes"
                  }
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
                    subtitle={
                      scale === "log"
                        ? "Absolute successive log-time differences · dimensionless log ratio"
                        : "Absolute difference between consecutive calls · minutes"
                    }
                    points={selected.imr.points
                      .filter((p) => p.moving_range != null)
                      .map((p) => ({ ...p, signal: p.mr_signal }))}
                    value="moving_range"
                    center={selected.imr.mr_center}
                    lower={0}
                    upper={selected.imr.mr_ucl}
                  />
                  <Chart
                    title="Above-target proportion"
                    subtitle={`${selected.p_chart.method === "beta_binomial" ? "Beta-binomial predictive" : "Binomial plug-in"} · ${aggregation}-day UTC buckets · limits adapt to n`}
                    limitLabel={
                      selected.p_chart.method === "beta_binomial"
                        ? "Predictive count limits"
                        : "Exact binomial count limits"
                    }
                    centerLabel={
                      selected.p_chart.method === "beta_binomial"
                        ? "Posterior predictive mean"
                        : "Observed baseline rate"
                    }
                    exact
                    points={selected.p_chart.points}
                    value="proportion"
                    center={selected.p_chart.center}
                    lower="lcl"
                    upper="ucl"
                    percent
                  />
                </div>
                <FaultTreeGuide
                  target={target}
                  selected={selected}
                  onOpenInsights={() => navigateTab("insights")}
                />
                <div className="workspace-next">
                  <p>
                    <strong>Ready to investigate?</strong> Inspect individual
                    calls and assign a follow-up action in the dispatch
                    workspace.
                  </p>
                  <button
                    className="secondary"
                    onClick={() => navigateTab("operations")}
                  >
                    Open dispatch workspace <ArrowUpRight size={14} />
                  </button>
                </div>
              </>
            )}
          </section>
          <section
            id="panel-operations"
            role="tabpanel"
            aria-labelledby="tab-operations"
            hidden={tab !== "operations"}
            tabIndex={0}
          >
            <div className="workspace-intro panel">
              <h2>From a dispatch to a reviewed response</h2>
              <p>
                Start a call and record its arrival, or log a response that has
                already finished. Inspect the completed point against its own
                zone reference, then assign follow-up for the focus zone.
              </p>
              <p>
                <strong>
                  {summary?.count.toLocaleString() || "—"} completed{" "}
                  {priority === "all" ? "all-priority" : priority + "-priority"}{" "}
                  responses
                </strong>{" "}
                in this analysis. Open calls stay separate until an arrival is
                recorded.
              </p>
            </div>
            <OpenCalls
              source={source}
              target={target}
              priority={priority}
              records={records}
              onComplete={completeOpen}
            />
            {result && (
              <CallInspection
                key={source}
                records={records}
                result={result}
                target={target}
                onZoneChange={setZone}
                isActive={tab === "operations"}
              />
            )}
            {selected && (
              <>
                <div className="section-heading">
                  <div>
                    <h2>{selected.zone} · investigation and follow-up</h2>
                    <p>Use the focus-zone selector to review another area.</p>
                  </div>
                </div>
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
                                {p.dispatched_at.replace("T", " ").slice(0, 16)}
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
                        Review the proportion chart and service-target
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
            {selected && (
              <ResolutionReviews
                key={`${source}:${selected.zone}`}
                source={source}
                zone={selected.zone}
              />
            )}
            <section className="panel completed-records">
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
          </section>
          <section
            id="panel-insights"
            role="tabpanel"
            aria-labelledby="tab-insights"
            hidden={tab !== "insights"}
            tabIndex={0}
          >
            <div className="workspace-intro panel">
              <h2>Explore the detail behind a signal</h2>
              <p>
                Check uncertainty, the reference period, recorded delay
                patterns, and period denominators. These details support the
                main charts and help plan an investigation.
              </p>
            </div>
            {summary && (
              <div className="metrics supporting-metrics">
                <Metric
                  label="95% CONFIDENCE INTERVAL"
                  value={`${pct(summary.late_ci_low)}–${pct(summary.late_ci_high)}`}
                  detail="All zones · all periods · Wilson above-target interval"
                  icon={<ShieldCheck />}
                />{" "}
                {selected && (
                  <Metric
                    label="FOCUS-ZONE 95% INTERVAL"
                    value={
                      pct(selected.late_ci_low) +
                      "–" +
                      pct(selected.late_ci_high)
                    }
                    detail={
                      selected.zone + " · all periods · above-target proportion"
                    }
                    icon={<ShieldCheck />}
                  />
                )}
              </div>
            )}
            {result?.comparison && (
              <Comparison
                title="All zones · baseline vs monitoring"
                data={result.comparison}
              />
            )}
            {selected && (
              <>
                <div className="section-heading">
                  <div>
                    <h2>{selected.zone} · supporting detail</h2>
                    <p>
                      All panels use the same priority and frozen reference as
                      the key statistics.
                    </p>
                  </div>
                </div>
                {selected.baseline_quality && (
                  <section className="panel baseline-quality">
                    <h3>
                      Baseline quality ·{" "}
                      {selected.baseline_quality.review_recommended
                        ? "review recommended"
                        : "initial checks passed"}
                    </h3>
                    <p>
                      {selected.baseline_quality.baseline_count} baseline calls
                      · {selected.baseline_quality.i_signals} individual signals
                      · {selected.baseline_quality.mr_signals} moving-range
                      signals · I-MR limits{" "}
                      {selected.baseline_quality.imr_limits_available
                        ? "available"
                        : "unavailable"}
                      .{" "}
                      {selected.baseline_quality.p_signals == null
                        ? "Predictive baseline proportion signals are not evaluated."
                        : `${selected.baseline_quality.p_signals} baseline proportion diagnostics.`}
                    </p>
                    {selected.baseline_quality.reasons.map((reason) => (
                      <p key={reason}>{reason}</p>
                    ))}
                    <small>
                      These checks cannot prove stability, independence,
                      representative sampling, or constant case mix.
                    </small>
                  </section>
                )}
                <DelayPatterns
                  overall={result.delay_patterns}
                  selected={selected.delay_patterns}
                  zone={selected.zone}
                />
                <div className="panel model-explanation">
                  <h3>
                    {selected.p_chart.method === "beta_binomial"
                      ? "Baseline uncertainty is included"
                      : "Fixed-risk binomial reference"}
                  </h3>
                  <p>
                    Observed baseline above-target rate:{" "}
                    <strong>{pct(selected.p_chart.baseline_late_rate)}</strong>.
                    Chart center:{" "}
                    <strong>{pct(selected.p_chart.center)}</strong> (
                    {selected.p_chart.method === "beta_binomial"
                      ? "posterior predictive mean"
                      : "observed baseline estimate"}
                    ).
                  </p>
                  {selected.p_chart.method === "beta_binomial" ? (
                    <p>
                      Jeffreys prior Beta({selected.p_chart.prior_alpha},{" "}
                      {selected.p_chart.prior_beta}) updates to Beta(
                      {fmt(selected.p_chart.posterior_alpha, 1)},{" "}
                      {fmt(selected.p_chart.posterior_beta, 1)}). Predictive
                      limits include uncertainty in the baseline risk estimate.
                      Baseline periods fitted this reference and are not
                      evaluated for predictive signals. Coverage is conditional
                      on the model; this is not a guaranteed frequentist
                      false-alarm rate.
                    </p>
                  ) : (
                    <p>
                      Binomial limits treat the observed baseline rate as fixed.
                      They omit uncertainty from estimating that rate, and
                      zero/all-late baselines have degenerate limits.
                    </p>
                  )}
                </div>
                <p className="period-note">
                  Buckets are anchored separately at baseline and monitoring
                  starts. Final buckets may be partial and should be treated as
                  provisional; missing calendar days are not zero-demand
                  observations.
                </p>
                <section className="panel daily-signals">
                  <div className="panel-heading">
                    <div>
                      <h3>Period proportion signals</h3>
                      <p>
                        Monitoring periods outside chosen count limits; inspect
                        period denominators and call mix.
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
                            <th>UTC period</th>
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
                                <td>
                                  {p.period_start || p.date} –{" "}
                                  {p.period_end || p.date}
                                </td>
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
                      <strong>No monitoring-period proportion signals</strong>
                      <p>
                        Absence of signals does not imply the service target is
                        met.
                      </p>
                    </div>
                  )}
                </section>
              </>
            )}
          </section>
          <div className="footnote" hidden={tab === "about"}>
            <ShieldCheck size={16} />
            <p>
              {result?.warnings?.join(" ") ||
                "Load a dataset to begin. Synthetic demonstrations do not establish a clinical standard."}{" "}
              The service target is a configurable planning threshold, not a
              clinical guarantee.
            </p>
          </div>
          {tab === "methods" && (
            <section className="panel methods">
              <h2 id="methods-title" tabIndex={-1}>
                Statistics before averages
              </h2>
              <p>
                ResponseWatch helps dispatch supervisors investigate variation
                in dispatch-to-on-scene times. It analyzes completed responses
                only; missing arrivals and canceled calls need a separate
                operational review.
              </p>
              <h3>Log I-MR by default</h3>
              <p>
                The first configured UTC calendar days form a frozen baseline.
                Calls are ordered by dispatch within zone. Default log I-MR
                models natural-log response times: limits are log mean ± 3 ×
                mean successive log moving range / 1.128, then exponentiated for
                display in minutes. The displayed center is a geometric mean.
                Log moving ranges are dimensionless log ratios; their upper
                limit is 3.267 × baseline mean log moving range. Raw-minute I-MR
                is also available. Nonpositive durations cannot use logarithms.
                Points strictly outside limits are flagged; no other run rules
                apply.
              </p>
              <h3>Proportion charts with baseline uncertainty</h3>
              <p>
                A response is above target only when its duration is strictly
                greater than the threshold. Default beta-binomial predictive
                limits combine a Jeffreys Beta(0.5, 0.5) prior with baseline
                late/on-time counts. The posterior predictive mean is the
                center; observed baseline rate is reported separately.
                Predictive count quantiles use equal tails totaling 0.002699796.
                Counts strictly outside discrete bounds signal. These limits
                account for uncertainty in baseline risk but depend on a
                constant-risk independent-binomial model; they do not guarantee
                a frequentist false-alarm rate. Baseline periods are fitted
                references, not evaluated predictive tests.
              </p>
              <p>
                The optional exact-binomial plug-in chart treats observed
                baseline risk as known, omits estimation uncertainty, and
                degenerates for zero/all-late baselines. Both methods use each
                bucket's actual count; 1- or 7-day UTC bins are anchored
                separately in baseline and monitoring, empty bins omitted, final
                partial bins provisional. Small samples and case-mix changes
                still require judgment.
              </p>
              <h3>Before and after</h3>
              <p>
                Compare completed-call count, above-target proportion with a 95%
                Wilson interval, and interpolated 90th-percentile response time
                between the fixed baseline and later observations.
                Percentage-point and minute differences are descriptive, not
                causal treatment effects or significance tests. Priority
                defaults to high to reduce case-mix confounding. Unequal
                periods, missing calls, changes in workload and priority
                assignment can distort comparisons.
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
              <h3>Logged context and missingness</h3>
              <p>
                Optional shift, traffic and units_available columns support
                unadjusted condition comparisons and are preserved in CSV
                export. Units available must be a nonnegative integer when
                supplied. Blank context remains “Not recorded”; it is never
                interpreted as no delay. Reason coverage is shown for all calls
                and above-target calls separately. The Pareto view includes
                missing reasons in its denominator so incomplete logging remains
                visible.
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
          {tab === "about" && <AboutPage />}
          <footer>
            ResponseWatch{" "}
            <span>
              Quality control for emergency response · Synthetic demonstration
              data
            </span>
            <button
              className="text-button"
              onClick={() => navigateTab("methods")}
            >
              Methods & guidance
            </button>
            <button
              className="text-button"
              onClick={() => navigateTab("about")}
            >
              About
            </button>
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
function Comparison({ title, data }) {
  const b = data.baseline,
    m = data.monitoring;
  return (
    <section className="panel comparison">
      <div className="panel-heading">
        <div>
          <h3>{title}</h3>
          <p>
            Same priority and target · observed completed calls only ·
            descriptive comparison
          </p>
        </div>
        <span className="small-badge">Frozen baseline</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Period</th>
              <th>Calls</th>
              <th>Above target</th>
              <th>95% Wilson interval</th>
              <th>90th percentile</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Baseline", b],
              ["Monitoring", m],
            ].map(([label, x]) => (
              <tr key={label}>
                <td>{label}</td>
                <td>{x?.count ?? "—"}</td>
                <td>{pct(x?.late_rate)}</td>
                <td>
                  {x
                    ? `${pct(x.late_ci_low)} – ${pct(x.late_ci_high)}`
                    : "No observations"}
                </td>
                <td>{x ? `${fmt(x.p90_minutes)} min` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="comparison-delta">
        <span>Monitoring − baseline</span>
        <strong>
          {data.late_rate_delta_pp == null
            ? "—"
            : `${data.late_rate_delta_pp > 0 ? "+" : ""}${fmt(data.late_rate_delta_pp)} percentage points above target`}
        </strong>
        <strong>
          {data.p90_delta_minutes == null
            ? "—"
            : `${data.p90_delta_minutes > 0 ? "+" : ""}${fmt(data.p90_delta_minutes)} min at p90`}
        </strong>
        <small>
          Negative differences indicate lower observed values. Not a causal
          effect.
        </small>
      </div>
    </section>
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
