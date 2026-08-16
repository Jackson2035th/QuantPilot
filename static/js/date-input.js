const strictDateMessage =
  "Enter a valid date in YYYY-MM-DD format using a four-digit year, a month from 01 to 12, and a valid day.";

function isValidStrictDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (year < 1000 || month < 1 || month > 12 || day < 1) return false;

  const candidate = new Date(Date.UTC(year, month - 1, day));
  return (
    candidate.getUTCFullYear() === year &&
    candidate.getUTCMonth() === month - 1 &&
    candidate.getUTCDate() === day
  );
}

function validateStrictDateInput(input) {
  if (!input.value) {
    input.setCustomValidity("");
    return;
  }
  input.setCustomValidity(isValidStrictDate(input.value) ? "" : strictDateMessage);
}

document.addEventListener("input", (event) => {
  if (event.target.matches("[data-strict-date]")) {
    validateStrictDateInput(event.target);
  }
});

document.addEventListener(
  "submit",
  (event) => {
    event.target.querySelectorAll("[data-strict-date]").forEach(validateStrictDateInput);
  },
  true,
);
