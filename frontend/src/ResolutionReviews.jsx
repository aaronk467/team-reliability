import React, { useEffect, useState } from "react";

const empty = {
  owner: "",
  status: "open",
  action: "",
  due_date: "",
  version: 0,
};
export default function ResolutionReviews({ source, zone }) {
  const [config, setConfig] = useState(null),
    [token, setToken] = useState("");
  const [shared, setShared] = useState(false),
    [items, setItems] = useState({});
  const [draft, setDraft] = useState(empty),
    [error, setError] = useState("");
  const [notice, setNotice] = useState(""),
    [broken, setBroken] = useState(false),
    [busy, setBusy] = useState(false);
  const key = `responsewatch:reviews:${source}`;
  useEffect(() => {
    let active = true;
    fetch("/api/reviews/config")
      .then((r) => {
        if (!r.ok) throw Error("Review configuration could not be read");
        return r.json();
      })
      .then((v) => active && setConfig(v))
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    setShared(false);
    setItems({});
    setNotice("");
    setError("");
    setBroken(false);
    try {
      const value = JSON.parse(localStorage.getItem(key) || "{}");
      if (
        !value ||
        Array.isArray(value) ||
        typeof value !== "object" ||
        Object.values(value).some(
          (x) =>
            !x ||
            typeof x.owner !== "string" ||
            !["open", "in_progress", "resolved"].includes(x.status) ||
            typeof x.action !== "string",
        )
      )
        throw Error("Invalid saved review format");
      setItems(value);
    } catch (e) {
      setBroken(true);
      setError(`Local reviews could not be read. Data preserved: ${e.message}`);
    }
  }, [key]);
  useEffect(() => {
    setDraft({
      ...empty,
      ...items[zone],
      due_date: items[zone]?.due_date || "",
    });
  }, [items, zone]);
  async function loadShared() {
    setBusy(true);
    setError("");
    const selectedSource = source;
    try {
      const r = await fetch(
        `/api/reviews?source=${encodeURIComponent(source)}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      const data = await r.json();
      if (!r.ok) throw Error(data.detail || "Could not load shared reviews");
      if (selectedSource !== source) return;
      setItems(Object.fromEntries(data.map((x) => [x.zone, x])));
      setShared(true);
      setNotice("Shared reviews loaded. Token is kept in memory only.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const row = {
        source,
        zone,
        ...draft,
        owner: draft.owner.trim(),
        action: draft.action.trim(),
        due_date: draft.due_date || null,
      };
      if (row.status !== "open" && !row.owner)
        throw Error("Assign a reviewer alias before progressing a review.");
      if (row.status === "resolved" && !row.action)
        throw Error("Document the action before resolving a review.");
      if (shared) {
        const r = await fetch("/api/reviews", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            source,
            zone,
            owner: row.owner,
            status: row.status,
            action: row.action,
            due_date: row.due_date,
            version: row.version,
          }),
        });
        const data = await r.json();
        if (!r.ok)
          throw Error(
            typeof data.detail === "string"
              ? data.detail
              : JSON.stringify(data.detail),
          );
        setItems((old) => ({ ...old, [zone]: data }));
        setNotice("Shared review saved.");
      } else {
        const next = {
          ...items,
          [zone]: {
            ...row,
            version: row.version + 1,
            updated_at: new Date().toISOString(),
          },
        };
        localStorage.setItem(key, JSON.stringify(next));
        setItems(next);
        setNotice(
          "Browser-local review saved. Export a backup; it is not shared with other users.",
        );
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function exportReviews() {
    const raw = broken
      ? localStorage.getItem(key)
      : JSON.stringify(items, null, 2);
    const url = URL.createObjectURL(
      new Blob([raw || "{}"], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "responsewatch-review-backup.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section className="panel resolution-reviews">
      <div className="panel-heading">
        <div>
          <h3>Resolution review · {zone}</h3>
          <p>
            Assign a reviewer alias, document an action, and plan a follow-up.
            This register does not change statistical limits.
          </p>
        </div>
        <span className="small-badge">
          {shared ? "Shared server register" : "Browser-local register"}
        </span>
      </div>
      <div className="review-content">
        <p className="table-note">
          {config?.message || "Checking optional shared storage…"} Use
          synthetic, nonpersonal reviewer aliases and notes.
        </p>
        {config?.shared_enabled && (
          <div className="button-row">
            <label>
              Shared review token
              <input
                aria-label="Shared review token"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                autoComplete="off"
              />
            </label>
            <button
              className="secondary"
              disabled={busy || !token}
              onClick={loadShared}
            >
              Load shared reviews
            </button>
          </div>
        )}
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {notice && (
          <div className="notice" role="status">
            {notice}
          </div>
        )}
        {broken ? (
          <div className="button-row">
            <button className="secondary" onClick={exportReviews}>
              Export preserved review data
            </button>
            <button
              className="secondary"
              onClick={() => {
                if (
                  window.confirm(
                    "Clear unreadable local reviews? Export a backup first.",
                  )
                ) {
                  localStorage.removeItem(key);
                  setItems({});
                  setBroken(false);
                  setError("");
                }
              }}
            >
              Clear unreadable reviews
            </button>
          </div>
        ) : (
          <form className="review-form" onSubmit={save}>
            <label>
              Reviewer alias
              <input
                name="review-owner"
                maxLength={120}
                value={draft.owner}
                onChange={(e) => setDraft({ ...draft, owner: e.target.value })}
              />
            </label>
            <label>
              Review status
              <select
                name="review-status"
                value={draft.status}
                onChange={(e) => setDraft({ ...draft, status: e.target.value })}
              >
                <option value="open">Open</option>
                <option value="in_progress">In progress</option>
                <option value="resolved">Resolved</option>
              </select>
            </label>
            <label>
              Follow-up date
              <input
                name="review-due"
                type="date"
                value={draft.due_date}
                onChange={(e) =>
                  setDraft({ ...draft, due_date: e.target.value })
                }
              />
            </label>
            <label className="review-action">
              Action and follow-up notes
              <textarea
                name="review-action"
                rows={3}
                maxLength={4000}
                value={draft.action}
                onChange={(e) => setDraft({ ...draft, action: e.target.value })}
              />
            </label>
            <div className="button-row">
              <button className="primary" disabled={busy || !source || !zone}>
                Save review
              </button>
              <button
                className="secondary"
                type="button"
                onClick={exportReviews}
              >
                Export review backup
              </button>
            </div>
          </form>
        )}
      </div>
    </section>
  );
}
