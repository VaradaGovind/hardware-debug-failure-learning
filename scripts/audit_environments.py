import sys

def audit():
    print("Python Executable:", sys.executable)
    print("Python Version:", sys.version.replace("\n", " "))
    pkgs = [
        ("torch", "torch"),
        ("transformers", "transformers"),
        ("peft", "peft"),
        ("accelerate", "accelerate"),
        ("torch_directml", "torch_directml"),
        ("yaml", "PyYAML"),
        ("pytest", "pytest"),
        ("vcd", "pyvcd"),
        ("matplotlib", "matplotlib"),
        ("sklearn", "scikit-learn"),
        ("pandas", "pandas"),
        ("numpy", "numpy")
    ]
    for mod_name, label in pkgs:
        try:
            m = __import__(mod_name)
            ver = getattr(m, "__version__", "installed")
            print(f"  {label:<15}: {ver}")
        except ImportError as e:
            print(f"  {label:<15}: NOT INSTALLED")

if __name__ == "__main__":
    audit()
