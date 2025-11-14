import subprocess
import sys
import os

# Используем полный путь к pyinstaller
pyinstaller_exe = r'C:\Users\a.zuev\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\pyinstaller.exe'

if not os.path.exists(pyinstaller_exe):
    print(f"PyInstaller не найден по пути: {pyinstaller_exe}")
    print("PyInstaller не установлен. Устанавливаю...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    pyinstaller_exe = r'C:\Users\a.zuev\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\pyinstaller.exe'

print(f"Используем PyInstaller: {pyinstaller_exe}")

# Команда сборки
cmd = [
    pyinstaller_exe,
    "--onefile",
    "--noconsole",
    "--name", "WeighingJournal",
    "--icon", "static/icon.ico",
    "--add-data", "static;static",
    "main.py"
]

print("Запуск сборки...")
result = subprocess.run(cmd, cwd=os.getcwd())
if result.returncode == 0:
    print("Сборка завершена успешно!")
    print("Исполняемый файл: dist/WeighingJournal.exe")
else:
    print(f"Ошибка сборки, код выхода: {result.returncode}")
    sys.exit(result.returncode)