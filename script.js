const currentEl = document.getElementById("current");
const historyEl = document.getElementById("history");

let current = "0";
let previous = null;
let operator = null;
let resetNext = false;

function compute(a, b, op) {
  switch (op) {
    case "+": return a + b;
    case "−": return a - b;
    case "×": return a * b;
    case "÷": return b === 0 ? NaN : a / b;
  }
}

function format(n) {
  if (!Number.isFinite(n)) return "خطأ";
  return String(parseFloat(n.toPrecision(12)));
}

function render() {
  currentEl.textContent = current;
  historyEl.textContent = operator ? `${previous} ${operator}` : "";
}

function inputNumber(ch) {
  if (current === "خطأ") clearAll();
  if (resetNext) { current = "0"; resetNext = false; }
  if (ch === ".") {
    if (!current.includes(".")) current += ".";
  } else {
    current = current === "0" ? ch : current + ch;
  }
  render();
}

function chooseOperator(op) {
  if (current === "خطأ") return;
  if (operator && !resetNext) equals(true);
  previous = current;
  operator = op;
  resetNext = true;
  render();
}

function equals(keepChain = false) {
  if (!operator || current === "خطأ") return;
  const result = format(compute(parseFloat(previous), parseFloat(current), operator));
  historyEl.textContent = `${previous} ${operator} ${current} =`;
  current = result;
  if (!keepChain) { operator = null; previous = null; }
  resetNext = true;
  currentEl.textContent = current;
  if (keepChain) return;
}

function clearAll() {
  current = "0";
  previous = null;
  operator = null;
  resetNext = false;
  render();
}

function deleteLast() {
  if (resetNext || current === "خطأ") return;
  current = current.length > 1 ? current.slice(0, -1) : "0";
  if (current === "-") current = "0";
  render();
}

function percent() {
  if (current === "خطأ") return;
  current = format(parseFloat(current) / 100);
  render();
}

function negate() {
  if (current === "0" || current === "خطأ") return;
  current = current.startsWith("-") ? current.slice(1) : "-" + current;
  render();
}

document.querySelector(".keys").addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  if (btn.dataset.num !== undefined) inputNumber(btn.dataset.num);
  else if (btn.dataset.op) chooseOperator(btn.dataset.op);
  else {
    switch (btn.dataset.action) {
      case "clear": clearAll(); break;
      case "delete": deleteLast(); break;
      case "percent": percent(); break;
      case "negate": negate(); break;
      case "equals": equals(); break;
    }
  }
});

document.addEventListener("keydown", (e) => {
  if (/^[0-9.]$/.test(e.key)) inputNumber(e.key);
  else if (e.key === "+") chooseOperator("+");
  else if (e.key === "-") chooseOperator("−");
  else if (e.key === "*") chooseOperator("×");
  else if (e.key === "/") { e.preventDefault(); chooseOperator("÷"); }
  else if (e.key === "Enter" || e.key === "=") { e.preventDefault(); equals(); }
  else if (e.key === "Backspace") deleteLast();
  else if (e.key === "Escape") clearAll();
  else if (e.key === "%") percent();
});
