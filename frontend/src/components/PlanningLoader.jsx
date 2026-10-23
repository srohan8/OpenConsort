import { useEffect, useState } from "react";

const MESSAGES = [
  "Asking the tiny model to think really hard...",
  "Teaching a hamster to read your idea...",
  "Sketching screens on a very small napkin...",
  "Arguing with the features about who goes first...",
  "Untangling the user flow spaghetti...",
  "Polishing the buttons nobody has clicked yet...",
  "Convincing the database it's a big deal...",
  "Counting modules. Lost count. Starting over...",
  "Running on a CPU, not a rocket. Worth the wait...",
  "Almost there. (The model says so, anyway.)",
];

const MESSAGE_MS = 3000;

export default function PlanningLoader() {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * MESSAGES.length));
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const message = setInterval(() => setIndex((i) => (i + 1) % MESSAGES.length), MESSAGE_MS);
    const clock = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => {
      clearInterval(message);
      clearInterval(clock);
    };
  }, []);

  return (
    <div className="planning-loader" role="status" aria-live="polite">
      <div className="loader-stage" aria-hidden="true">
        <div className="loader-bot">
          <span className="loader-antenna" />
          <span className="loader-eye left" />
          <span className="loader-eye right" />
          <span className="loader-mouth" />
        </div>
        <div className="loader-shadow" />
        <div className="loader-bars">
          <span className="loader-bar terracotta" />
          <span className="loader-bar mustard" />
          <span className="loader-bar sage" />
        </div>
      </div>
      <p className="loader-message" key={index}>
        {MESSAGES[index]}
      </p>
      <p className="loader-timer">
        Planning for {seconds}s - local models can take a minute or two
      </p>
    </div>
  );
}
