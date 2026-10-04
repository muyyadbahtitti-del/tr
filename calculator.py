import tkinter as tk


class Calculator:
    def __init__(self, root):
        self.root = root
        root.title("آلة حاسبة")
        root.configure(bg="#2a2c36")
        root.resizable(False, False)

        self.current = "0"
        self.previous = None
        self.operator = None
        self.reset_next = False

        self.history_var = tk.StringVar()
        self.current_var = tk.StringVar(value="0")

        tk.Label(root, textvariable=self.history_var, anchor="e", bg="#2a2c36",
                 fg="#8b8fa3", font=("Arial", 12)).grid(row=0, column=0, columnspan=4, sticky="ew", padx=12, pady=(12, 0))
        tk.Label(root, textvariable=self.current_var, anchor="e", bg="#2a2c36",
                 fg="white", font=("Arial", 32)).grid(row=1, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 8))

        keys = [
            ("C", "fn"), ("⌫", "fn"), ("%", "fn"), ("÷", "op"),
            ("7", "num"), ("8", "num"), ("9", "num"), ("×", "op"),
            ("4", "num"), ("5", "num"), ("6", "num"), ("−", "op"),
            ("1", "num"), ("2", "num"), ("3", "num"), ("+", "op"),
            ("±", "fn"), ("0", "num"), (".", "num"), ("=", "eq"),
        ]
        colors = {"num": "#3a3d4a", "fn": "#4b4f61", "op": "#ff9f0a", "eq": "#30b46c"}
        for i, (label, kind) in enumerate(keys):
            tk.Button(root, text=label, width=4, height=2, font=("Arial", 16),
                      bg=colors[kind], fg="white", activebackground=colors[kind],
                      relief="flat", command=lambda l=label: self.press(l)
                      ).grid(row=2 + i // 4, column=i % 4, padx=4, pady=4)

        root.bind("<Key>", self.on_key)

    @staticmethod
    def compute(a, b, op):
        if op == "+": return a + b
        if op == "−": return a - b
        if op == "×": return a * b
        if op == "÷": return float("nan") if b == 0 else a / b

    @staticmethod
    def fmt(n):
        if n != n or n in (float("inf"), float("-inf")):
            return "خطأ"
        return str(float(f"{n:.12g}")).removesuffix(".0")

    def render(self):
        self.current_var.set(self.current)
        self.history_var.set(f"{self.previous} {self.operator}" if self.operator else "")

    def press(self, key):
        if self.current == "خطأ" and key not in ("C",):
            self.clear()
        if key.isdigit() or key == ".":
            if self.reset_next:
                self.current, self.reset_next = "0", False
            if key == ".":
                if "." not in self.current:
                    self.current += "."
            else:
                self.current = key if self.current == "0" else self.current + key
        elif key in "+−×÷":
            if self.operator and not self.reset_next:
                self.equals(chain=True)
            self.previous, self.operator, self.reset_next = self.current, key, True
        elif key == "=":
            self.equals()
        elif key == "C":
            self.clear()
        elif key == "⌫":
            if not self.reset_next:
                self.current = self.current[:-1] or "0"
                if self.current == "-":
                    self.current = "0"
        elif key == "%":
            self.current = self.fmt(float(self.current) / 100)
        elif key == "±":
            if self.current != "0":
                self.current = self.current[1:] if self.current.startswith("-") else "-" + self.current
        self.render()

    def equals(self, chain=False):
        if not self.operator:
            return
        result = self.fmt(self.compute(float(self.previous), float(self.current), self.operator))
        self.history_var.set(f"{self.previous} {self.operator} {self.current} =")
        self.current = result
        if not chain:
            self.operator = self.previous = None
        self.reset_next = True
        self.current_var.set(self.current)
        if not chain:
            return

    def clear(self):
        self.current, self.previous, self.operator, self.reset_next = "0", None, None, False
        self.render()

    def on_key(self, e):
        c = e.char
        mapping = {"-": "−", "*": "×", "/": "÷"}
        if c.isdigit() or c in ".+%":
            self.press(c)
        elif c in mapping:
            self.press(mapping[c])
        elif e.keysym in ("Return", "KP_Enter") or c == "=":
            self.press("=")
        elif e.keysym == "BackSpace":
            self.press("⌫")
        elif e.keysym == "Escape":
            self.press("C")


if __name__ == "__main__":
    root = tk.Tk()
    Calculator(root)
    root.mainloop()
