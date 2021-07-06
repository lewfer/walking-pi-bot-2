mode = "Turtle"
try:
    f = open("mode.txt", "r")
    mode = f.read()
    mode = mode.strip()
except Exception:
    pass

print("-" + mode + "-")

exec("print('abc')")
