// Mock data for the UI shell prototype, per doc/kickoff-brief-ui-shell.md.
// Shaped to roughly match the module-grouped LockedSpec/UserFlow structure
// described in doc/architecture.md's "Platform UI Structure" section -
// close enough that swapping in real orchestrator output later is a
// data-shape change, not a rewrite.
//
// NOTE: locked_spec.schema.json still defines `features` as a flat array as
// of this writing - the module-grouped shape below is what architecture.md
// flags the schema as needing to change TO. This mock uses that target shape
// directly rather than the flat-array shape the schema currently has.

export const lockedSpec = {
  product_type: "web_app",
  modules: [
    {
      module_number: 1,
      module_name: "Account & auth",
      features: ["Sign up with email + password", "Verify email with a one-time code"],
    },
    {
      module_number: 2,
      module_name: "Task management",
      features: ["Add a task with title", "View all active tasks", "Mark a task complete"],
    },
    {
      module_number: 3,
      module_name: "Progress tracking",
      features: ["View a summary of completed vs. total tasks"],
    },
  ],
};

// Plain-English module title, per the "title hierarchy" convention:
// small technical label above a larger plain-English heading.
export const moduleTitles = {
  1: { technicalLabel: "Module 1 · Account & auth", plainTitle: "Sign up and verify your account" },
  2: { technicalLabel: "Module 2 · Task management", plainTitle: "Add, view, and complete your to-dos" },
  3: { technicalLabel: "Module 3 · Progress tracking", plainTitle: "See how much you've gotten done" },
};

export const moduleColors = {
  1: "#8b7fa8", // muted purple (satin finish, desaturated from bright #7c3aed)
  2: "#6e8fa8", // muted blue (satin finish, desaturated from bright #2563eb)
  3: "#7a9b7a", // muted green (satin finish, desaturated from bright #059669)
};

// UserFlow: screens as nodes + transitions between them, per
// orchestrator/schemas/user_flow.schema.json's shape (id/name/purpose,
// from/to/trigger), extended with module_number (for cross-tab tagging),
// reached_from (plain-language context for the detail panel), and an
// actions list each marked done/planned - mock-only extensions the real
// schema doesn't have yet.
export const userFlow = {
  screens: [
    {
      id: "signup",
      module_number: 1,
      name: "Sign up",
      purpose: "Create a new account with an email and password.",
      reached_from: "First screen a new user sees.",
      actions: [
        { label: "Enter email and password", done: true },
        { label: "Submit the sign-up form", done: true },
        { label: "Show a friendly error if the email is already taken", done: false },
      ],
    },
    {
      id: "verify-email",
      module_number: 1,
      name: "Verify email",
      purpose: "Confirm the new account by entering a one-time code sent by email.",
      reached_from: "Reached automatically after signing up.",
      actions: [
        { label: "Enter the 6-digit code", done: true },
        { label: "Resend the code if it expired", done: false },
      ],
    },
    {
      id: "add-task",
      module_number: 2,
      name: "Add task",
      purpose: "Create a new to-do item with a title.",
      reached_from: "Reached from the Task list screen via the \"Add task\" button.",
      actions: [
        { label: "Enter a task title", done: true },
        { label: "Save the task to the list", done: true },
      ],
    },
    {
      id: "task-list",
      module_number: 2,
      name: "Task list",
      purpose: "View all active tasks in one place.",
      reached_from: "Reached after verifying your email, or from any other screen via the main menu.",
      actions: [
        { label: "See all active tasks", done: true },
        { label: "Open a task to mark it complete", done: true },
        { label: "Sort tasks by due date", done: false },
      ],
    },
    {
      id: "complete-task",
      module_number: 2,
      name: "Complete task",
      purpose: "Mark a task as finished.",
      reached_from: "Reached from the Task list screen by selecting a task.",
      actions: [
        { label: "Mark the task as done", done: true },
        { label: "Undo marking it done", done: false },
      ],
    },
    {
      id: "progress-summary",
      module_number: 3,
      name: "Progress summary",
      purpose: "See how many tasks are done out of the total.",
      reached_from: "Reached from the Task list screen via the \"Progress\" tab.",
      actions: [
        { label: "Show completed vs. total task count", done: false },
        { label: "Show a simple progress bar", done: false },
      ],
    },
  ],
  transitions: [
    { from: "signup", to: "verify-email", trigger: "submit sign-up form" },
    { from: "verify-email", to: "task-list", trigger: "enter correct code" },
    { from: "task-list", to: "add-task", trigger: "click \"Add task\"" },
    { from: "add-task", to: "task-list", trigger: "save task" },
    { from: "task-list", to: "complete-task", trigger: "select a task" },
    { from: "complete-task", to: "task-list", trigger: "mark done" },
    { from: "task-list", to: "progress-summary", trigger: "click \"Progress\"" },
  ],
};

// Development tab: module-tagged build status, plain-language by default.
export const developmentStatus = [
  {
    module_number: 1,
    status: "done",
    label: "Auth endpoints built and tested",
    logStub:
      "POST /signup -> 201\nPOST /verify-email -> 200\n5/5 checks passed",
  },
  {
    module_number: 2,
    status: "done",
    label: "Task endpoints built and tested",
    logStub:
      "POST /tasks -> 201\nGET /tasks -> 200\nPATCH /tasks/{id}/complete -> 200\n6/6 checks passed",
  },
  {
    module_number: 3,
    status: "in-progress",
    label: "Building progress stats endpoint...",
    logStub: "GET /progress -> writing response_model...",
  },
];

function computeModuleCounts() {
  const counts = {};
  for (const screen of userFlow.screens) {
    const m = screen.module_number;
    if (!counts[m]) counts[m] = { done: 0, total: 0 };
    for (const action of screen.actions) {
      counts[m].total += 1;
      if (action.done) counts[m].done += 1;
    }
  }
  return counts;
}

export const moduleActionCounts = computeModuleCounts();
