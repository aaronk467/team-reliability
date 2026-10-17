import React from "react";
import "./AboutPage.css";

const developers = [
  "Rafael Tassari",
  "Aaron Kumar",
  "Simon Cespedes",
  "Charlie Liu",
];

export default function AboutPage() {
  return (
    <section className="panel about-page" aria-label="About ResponseWatch">
      <div className="about-purpose">
        <span className="overview-guide-eyebrow">Our purpose</span>
        <p>
          ResponseWatch helps ambulance dispatch supervisors monitor
          dispatch-to-on-scene response times, spot unusual changes across
          service zones, and prioritize follow-up. It combines statistical
          process control, response logging, and recorded delay context to
          support quality improvement.
        </p>
      </div>
      <div className="about-team">
        <h2>Developed by</h2>
        <ul className="about-developers">
          {developers.map((name) => (
            <li key={name}>
              <span className="about-initials" aria-hidden="true">
                {name
                  .split(" ")
                  .map((part) => part[0])
                  .join("")}
              </span>
              <span>{name}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
