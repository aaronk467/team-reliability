import React, { useEffect, useMemo, useRef, useState } from "react";
import "./CallInspection.css";

const minutes = (value) =>
  Number.isFinite(value) ? `${value.toFixed(2)} min` : "Unavailable";

function ResponsePosition({ point, chart, target, limitsAvailable }) {
  const width = 720;
  const left = 30;
  const right = width - 30;
  const observed = [point.minutes, target, chart.center];
  if (limitsAvailable) observed.push(chart.lcl, chart.ucl);
  const maximum = Math.max(1, ...observed.filter(Number.isFinite)) * 1.12;
  const x = (value) => left + (value / maximum) * (right - left);
  const titleId = React.useId();
  const descriptionId = React.useId();
  return (
    <figure className="call-inspection-position">
      <svg
        viewBox={`0 0 ${width} 130`}
        role="img"
        aria-labelledby={`${titleId} ${descriptionId}`}
      >
        <title id={titleId}>
          Selected response against target and individual limits
        </title>
        <desc id={descriptionId}>
          Response {minutes(point.minutes)}; service target {minutes(target)}.
          {limitsAvailable
            ? ` Frozen individual limits ${minutes(chart.lcl)} to ${minutes(chart.ucl)}; baseline center ${minutes(chart.center)}.`
            : " Individual control limits are unavailable for this response."}
          The horizontal position is in minutes on a linear display.
        </desc>
        <line
          x1={left}
          y1="75"
          x2={right}
          y2="75"
          className="inspection-axis"
        />
        {limitsAvailable && (
          <g>
            <rect
              x={x(chart.lcl)}
              y="63"
              width={Math.max(0, x(chart.ucl) - x(chart.lcl))}
              height="24"
              rx="5"
              className="inspection-limit-band"
            />
            {[chart.lcl, chart.ucl].map((value, index) => (
              <line
                key={index}
                x1={x(value)}
                y1="54"
                x2={x(value)}
                y2="96"
                className="inspection-limit-tick"
              />
            ))}
          </g>
        )}
        {Number.isFinite(chart.center) && (
          <line
            x1={x(chart.center)}
            y1="57"
            x2={x(chart.center)}
            y2="93"
            className="inspection-center-tick"
          />
        )}
        {Number.isFinite(target) && (
          <g>
            <line
              x1={x(target)}
              y1="42"
              x2={x(target)}
              y2="97"
              className="inspection-target-tick"
            />
            <text
              x={x(target)}
              y="32"
              textAnchor="middle"
              className="inspection-target-label"
            >
              Target
            </text>
          </g>
        )}
        <circle
          cx={x(point.minutes)}
          cy="75"
          r="8"
          className="inspection-response-dot"
        />
        <text x={left} y="118" className="inspection-axis-label">
          0 min
        </text>
        <text
          x={right}
          y="118"
          textAnchor="end"
          className="inspection-axis-label"
        >
          {minutes(maximum)}
        </text>
      </svg>
      <figcaption>
        <span>
          <i className="inspection-dot-key" /> Selected response
        </span>
        <span>
          <i className="inspection-target-key" /> Service target
        </span>
        {limitsAvailable && (
          <span>
            <i className="inspection-band-key" /> Frozen individual-limit range
          </span>
        )}
      </figcaption>
    </figure>
  );
}

export default function CallInspection({
  records = [],
  result,
  target,
  onZoneChange,
  isActive = true,
}) {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [newCall, setNewCall] = useState("");
  const previousRecords = useRef(records);
  const pendingAdded = useRef([]);
  const zoneCallback = useRef(onZoneChange);
  zoneCallback.current = onZoneChange;

  const entries = useMemo(() => {
    const pointMap = new Map();
    for (const zone of result?.zones || []) {
      for (const point of zone.imr.points) {
        pointMap.set(point.id, { point, chart: zone.imr, zone: zone.zone });
      }
    }
    const available = [];
    for (let index = records.length - 1; index >= 0; index -= 1) {
      const record = records[index];
      const match = pointMap.get(record.id);
      if (match) available.push({ ...match, record });
    }
    return available;
  }, [records, result]);
  const byId = useMemo(
    () => new Map(entries.map((entry) => [entry.point.id, entry])),
    [entries],
  );

  useEffect(() => {
    if (records !== previousRecords.current) {
      if (records.length > previousRecords.current.length) {
        pendingAdded.current = records
          .slice(previousRecords.current.length)
          .filter(
            (record) =>
              result?.priority === "all" ||
              record.priority === result?.priority,
          )
          .map((record) => record.id)
          .reverse();
      }
      previousRecords.current = records;
    }
    const added = pendingAdded.current.find((id) => byId.has(id));
    if (added) {
      setSelectedId(added);
      setNewCall(added);
      if (isActive) zoneCallback.current?.(byId.get(added).zone);
      pendingAdded.current = [];
    } else if (!byId.has(selectedId) && entries.length) {
      setSelectedId(entries[0].point.id);
      setNewCall("");
    }
  }, [records, entries, byId, selectedId, isActive]);

  const selected = byId.get(selectedId);
  const query = search.trim().toLocaleLowerCase();
  const matching = useMemo(
    () =>
      entries.filter((entry) =>
        entry.point.id.toLocaleLowerCase().includes(query),
      ),
    [entries, query],
  );
  const options = matching.slice(0, 100);
  const keepSelectedOption =
    selected && !options.some((entry) => entry.point.id === selectedId);
  const effectiveTarget = Number.isFinite(result?.target_minutes)
    ? result.target_minutes
    : Number(target);

  function selectCall(id) {
    setSelectedId(id);
    setNewCall("");
    const entry = byId.get(id);
    if (entry) zoneCallback.current?.(entry.zone);
  }

  return (
    <section
      className="panel call-inspection"
      aria-labelledby="call-inspection-heading"
    >
      <div className="panel-heading">
        <div>
          <h3 id="call-inspection-heading">Inspect a completed response</h3>
          <p>
            Find a call and see its actual response against its zone's frozen
            baseline limits and the service target. Current priority filter
            applies.
          </p>
        </div>
      </div>
      <div className="call-inspection-controls">
        <label>
          Find completed call
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by call ID"
          />
        </label>
        <label>
          Completed response to inspect
          <select
            aria-label="Completed response to inspect"
            value={selectedId}
            onChange={(event) => selectCall(event.target.value)}
            disabled={!entries.length}
          >
            {!selected && <option value="">Choose a completed response</option>}
            {keepSelectedOption && (
              <option value={selectedId}>
                {selectedId} · {selected.zone} (selected call)
              </option>
            )}
            {options.map((entry) => (
              <option key={entry.point.id} value={entry.point.id}>
                {entry.point.id} · {entry.zone} · {minutes(entry.point.minutes)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="call-inspection-search-note">
        {entries.length
          ? `${matching.length} matching call${matching.length === 1 ? "" : "s"}. ${matching.length > 100 ? "Showing the latest 100 by input order; narrow your call-ID search to find others." : "Latest input records appear first."}`
          : "No completed responses match the current analysis. Record an arrival or choose a priority with completed calls."}
        {matching.length === 0 &&
          entries.length > 0 &&
          " The selected call remains visible below."}
      </p>
      {newCall && (
        <p className="call-inspection-new" role="status">
          New completed response selected: {newCall}
        </p>
      )}
      {selected &&
        (() => {
          const { point, chart, record, zone } = selected;
          const limitsAvailable =
            Number.isFinite(chart.lcl) &&
            Number.isFinite(chart.ucl) &&
            (chart.scale !== "log" || point.minutes > 0);
          const aboveTarget = point.minutes > effectiveTarget;
          const targetStatus = aboveTarget
            ? "Above service target"
            : point.minutes === effectiveTarget
              ? "At service target"
              : "Below service target";
          const individualStatus = !limitsAvailable
            ? "Individual limits unavailable"
            : point.signal
              ? "Outside individual limits"
              : "Inside individual limits";
          const mrAvailable =
            Number.isFinite(point.moving_range) &&
            Number.isFinite(chart.mr_ucl);
          return (
            <div
              className="call-inspection-detail"
              aria-label="Selected completed response"
            >
              <div className="call-inspection-identity">
                <div>
                  <h4>{point.id}</h4>
                  <p>
                    {zone} · {record.priority} priority ·{" "}
                    {point.in_baseline
                      ? "Baseline period"
                      : "Monitoring period"}
                  </p>
                </div>
                <strong className="call-inspection-duration">
                  {minutes(point.minutes)}
                </strong>
              </div>
              <div className="call-inspection-statuses">
                <span
                  className={
                    aboveTarget
                      ? "inspection-status attention"
                      : "inspection-status"
                  }
                >
                  {targetStatus}
                </span>
                <span
                  className={
                    limitsAvailable && point.signal
                      ? "inspection-status attention"
                      : "inspection-status"
                  }
                >
                  {individualStatus}
                </span>
              </div>
              <p className="call-inspection-distinction">
                Missing the service target and being statistically unusual are
                different questions. A response can exceed the target while
                remaining inside the baseline limits.
              </p>
              <ResponsePosition
                point={point}
                chart={chart}
                target={effectiveTarget}
                limitsAvailable={limitsAvailable}
              />
              <dl className="call-inspection-values">
                <div>
                  <dt>Service target</dt>
                  <dd>{minutes(effectiveTarget)}</dd>
                </div>
                <div>
                  <dt>
                    Baseline center{chart.scale === "log" ? " (geometric)" : ""}
                  </dt>
                  <dd>{minutes(chart.center)}</dd>
                </div>
                <div>
                  <dt>Lower individual limit</dt>
                  <dd>
                    {limitsAvailable ? minutes(chart.lcl) : "Unavailable"}
                  </dd>
                </div>
                <div>
                  <dt>Upper individual limit</dt>
                  <dd>
                    {limitsAvailable ? minutes(chart.ucl) : "Unavailable"}
                  </dd>
                </div>
              </dl>
              <p className="call-inspection-mr">
                <strong>
                  {!mrAvailable
                    ? "Moving-range assessment unavailable"
                    : point.mr_signal
                      ? "Moving-range signal"
                      : "No moving-range signal"}
                  .
                </strong>{" "}
                {mrAvailable
                  ? `Change from the preceding call in this zone and priority filter: ${point.moving_range.toFixed(2)} ${chart.mr_units}; upper moving-range limit ${chart.mr_ucl.toFixed(2)} ${chart.mr_units}. This assesses the change between two calls, separately from this call's individual response.`
                  : "This call needs a usable preceding response and available baseline moving-range limits for that comparison."}
              </p>
              {!limitsAvailable && (
                <p className="call-inspection-caution">
                  No individual outlier assessment is available. Check the
                  zone's baseline warnings; a zero-minute response also cannot
                  be assessed on the log scale. The service-target comparison
                  still applies.
                </p>
              )}
              {point.in_baseline && (
                <p className="call-inspection-caution">
                  This call belongs to the baseline used to estimate the limits.
                  Its chart flags are baseline diagnostics, rather than an
                  independent monitoring test.
                </p>
              )}
              <p className="call-inspection-footnote">
                The response, limits and signal flags come from the Python
                analysis. This view does not change the baseline or establish a
                cause or patient outcome.
              </p>
            </div>
          );
        })()}
    </section>
  );
}
