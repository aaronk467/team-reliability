import React, { useEffect, useRef, useState } from "react";
import { Plus, Clock3, AlertTriangle } from "lucide-react";
const localNow = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 19);
};
const validRows = (rows) =>
  Array.isArray(rows) &&
  rows.every(
    (r) =>
      r &&
      typeof r.id === "string" &&
      r.id.trim() &&
      typeof r.zone === "string" &&
      r.zone.trim() &&
      ["high", "standard"].includes(r.priority) &&
      Number.isFinite(Date.parse(r.dispatched_at)),
  );
export default function OpenCalls({
  source,
  target,
  priority,
  records,
  onComplete,
}) {
  const [calls, setCalls] = useState([]),
    [storageError, setStorageError] = useState(""),
    [error, setError] = useState(""),
    [show, setShow] = useState(false),
    [now, setNow] = useState(Date.now()),
    [saving, setSaving] = useState(false);
  const key = `responsewatch:pending:${source}`;
  const activeSource = useRef(source);
  activeSource.current = source;
  useEffect(() => {
    setCalls([]);
    setError("");
    setShow(false);
    setStorageError("");
    if (!source) return;
    try {
      const parsed = JSON.parse(localStorage.getItem(key) || "[]");
      if (
        !validRows(parsed) ||
        new Set(parsed.map((r) => r.id)).size !== parsed.length
      )
        throw Error("Invalid saved open-call format");
      setCalls(parsed);
    } catch (e) {
      setStorageError(
        `Saved open calls could not be read (${e.message}). Data has been preserved. Export or explicitly clear it before adding calls.`,
      );
    }
  }, [key, source]);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 10000);
    return () => clearInterval(timer);
  }, []);
  function persist(rows) {
    localStorage.setItem(key, JSON.stringify(rows));
    setCalls(rows);
    setNow(Date.now());
  }
  function start(e) {
    e.preventDefault();
    try {
      const row = Object.fromEntries(new FormData(e.target));
      row.id = row.id.trim();
      row.zone = row.zone.trim();
      row.dispatched_at = new Date(row.dispatched_at).toISOString();
      if (!row.id || !row.zone) throw Error("ID and zone cannot be blank.");
      if (Date.parse(row.dispatched_at) > Date.now())
        throw Error("Dispatch time cannot be in the future.");
      if ([...calls, ...records].some((r) => r.id.trim() === row.id))
        throw Error("Call ID already exists.");
      persist([...calls, row]);
      setShow(false);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }
  async function arrive(e, row) {
    e.preventDefault();
    const startedSource = source;
    setSaving(true);
    try {
      const f = Object.fromEntries(new FormData(e.target));
      const complete = {
        ...row,
        arrived_at: new Date(f.arrived_at).toISOString(),
        delay_reason: f.delay_reason,
      };
      if (Date.parse(complete.arrived_at) < Date.parse(row.dispatched_at))
        throw Error("Arrival must be at or after dispatch.");
      if (Date.parse(complete.arrived_at) > Date.now() + 1000)
        throw Error("Arrival cannot be in the future.");
      const remaining = calls.filter((r) => r.id !== row.id);
      await onComplete(complete, () => {
        if (activeSource.current !== startedSource)
          throw Error("Source changed; pending call preserved.");
        persist(remaining);
      });
      if (activeSource.current === startedSource) setError("");
    } catch (e) {
      if (activeSource.current === startedSource) setError(e.message);
    } finally {
      setSaving(false);
    }
  }
  const visible = calls.filter(
      (r) => priority === "all" || r.priority === priority,
    ),
    overdue = visible.filter(
      (r) => (now - Date.parse(r.dispatched_at)) / 60000 > Number(target),
    );
  function exportRaw() {
    try {
      const blob = new Blob([localStorage.getItem(key) || "[]"], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob),
        a = document.createElement("a");
      a.href = url;
      a.download = "responsewatch-open-call-backup.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    }
  }
  return (
    <section className="panel open-calls">
      <div className="panel-heading">
        <div>
          <h3>
            <Clock3 size={15} /> Open dispatches{" "}
            <span className="small-badge">
              {visible.length} {priority === "all" ? "all-priority" : priority}{" "}
              open · {overdue.length} overdue
            </span>
          </h3>
          <p>
            Browser-local demo · refreshes every 10 seconds · open calls are
            excluded from every completed-response denominator.
          </p>
        </div>
        <button
          className="secondary"
          disabled={!source || !!storageError || saving}
          onClick={() => setShow(!show)}
        >
          <Plus size={15} /> Start dispatch
        </button>
      </div>
      {storageError && (
        <div className="error" role="alert">
          <div>
            {storageError}
            <div className="button-row">
              <button onClick={exportRaw}>Export saved data</button>
              <button
                onClick={() => {
                  if (
                    window.confirm(
                      "Clear unreadable browser-local open calls for this source? Export a backup first.",
                    )
                  ) {
                    try {
                      localStorage.removeItem(key);
                      setStorageError("");
                      setCalls([]);
                    } catch (e) {
                      setError(e.message);
                    }
                  }
                }}
              >
                Clear saved open calls
              </button>
            </div>
          </div>
        </div>
      )}
      {error && (
        <div className="error" role="alert">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}
      {show && (
        <form className="open-form" onSubmit={start}>
          <label>
            Call ID
            <input name="id" required />
          </label>
          <label>
            Zone
            <input name="zone" required />
          </label>
          <label>
            Priority
            <select
              name="priority"
              defaultValue={priority === "standard" ? "standard" : "high"}
            >
              <option value="high">High</option>
              <option value="standard">Standard</option>
            </select>
          </label>
          <label>
            Dispatched (browser local time)
            <input
              name="dispatched_at"
              type="datetime-local"
              step="1"
              defaultValue={localNow()}
              required
            />
          </label>
          <button className="primary" disabled={saving}>
            Start dispatch
          </button>
        </form>
      )}
      {visible.length ? (
        <div className="open-list">
          {visible.map((r) => {
            const elapsed = Math.max(
              0,
              (now - Date.parse(r.dispatched_at)) / 60000,
            );
            return (
              <div className="open-row" key={r.id}>
                <div>
                  <strong>
                    {r.id}{" "}
                    <span
                      className={elapsed > target ? "signal-tag" : "stable-tag"}
                    >
                      {elapsed > target ? "Over target" : "In progress"}
                    </span>
                  </strong>
                  <p>
                    {r.zone} · {r.priority} · {elapsed.toFixed(1)} min elapsed ·
                    dispatched {r.dispatched_at}
                  </p>
                </div>
                <form onSubmit={(e) => arrive(e, r)}>
                  <label>
                    Arrival (browser local time)
                    <input
                      aria-label={`Arrival time for ${r.id}`}
                      name="arrived_at"
                      type="datetime-local"
                      step="1"
                      required
                      defaultValue={localNow()}
                    />
                  </label>
                  <input
                    name="delay_reason"
                    aria-label={`Delay context for ${r.id}`}
                    placeholder="Delay context (optional)"
                  />
                  <button
                    className="secondary"
                    type="button"
                    onClick={(e) => {
                      e.currentTarget.form.elements.arrived_at.value =
                        localNow();
                    }}
                  >
                    Use now
                  </button>
                  <button
                    className="primary"
                    disabled={saving || !!storageError}
                  >
                    Record arrival
                  </button>
                </form>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="open-empty">
          No open dispatches match this priority.{" "}
          {calls.length > 0 &&
            `${calls.length} open dispatch(es) in other priorities.`}{" "}
          Start a dispatch to test elapsed-time monitoring.
        </div>
      )}
      <div className="open-disclosure">
        Not a production CAD or alerting system. Data stays in this browser and
        source ({source || "loading"}); closing this page stops the elapsed-time
        display. No patient information.
      </div>
    </section>
  );
}
