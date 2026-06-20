"""
Instala o app:
  1. Cria atalho no Desktop
  2. Adiciona ao startup do Windows (HKCU Run) para iniciar com a maquina

Execute uma vez: python install/create_shortcut.py
"""
import os
import sys
import winreg

STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "OperacaoAssistida"


def get_paths():
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script_path = os.path.join(root_dir, "main.py")
    return pythonw, script_path, root_dir


def create_desktop_shortcut(pythonw, script_path, script_dir):
    try:
        import win32com.client
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "pywin32"], check=True)
        import win32com.client

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Operação Assistida.lnk")

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = pythonw
    shortcut.Arguments = '-m main'
    shortcut.WorkingDirectory = script_dir
    shortcut.Description = "Operação Assistida — Monitoramento de Tarefas"
    shortcut.WindowStyle = 7  # minimizado — evita janela de console ao iniciar
    shortcut.save()

    print(f"  [ok] Atalho no Desktop: {shortcut_path}")


def add_to_startup(pythonw, root_dir):
    # Registry não suporta WorkingDirectory — usar wrapper /D para cmd /c não funciona
    # bem; a alternativa mais limpa é usar o próprio atalho .lnk do Desktop como target.
    # Aqui gravamos o comando direto; pythonw roda sem console e -m resolve imports.
    # WORKAROUND: gravar com /D via cmd /c causa flash. Melhor: referenciar o .lnk.
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Operação Assistida.lnk")
    # Chamar o atalho via shell garante WorkingDirectory correto sem console flash
    startup_cmd = f'"{shortcut_path}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_cmd)
    print(f"  [ok] Startup do Windows: {startup_cmd}")


def remove_from_startup():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        print("  [ok] Removido do startup.")
    except FileNotFoundError:
        print("  [--] Nao estava no startup.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true", help="Remove do startup")
    args = parser.parse_args()

    if args.uninstall:
        remove_from_startup()
    else:
        pythonw, script_path, script_dir = get_paths()
        print("Instalando Operação Assistida...")
        create_desktop_shortcut(pythonw, script_path, script_dir)
        add_to_startup(pythonw, script_dir)
        print("\nPronto. O app iniciara automaticamente com o Windows.")
