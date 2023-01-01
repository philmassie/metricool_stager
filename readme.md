# Metricool stager
- Small script for processing prepared jpgs for Instagram scheduling via metricool
- Images need captions in `caption` field

to add a `Send to` shortcut to the .ps1 launcher:
- note in `Target` escape space with backtick
- add `-NoExit to keep terminal alive`

```bash
# Target :
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoExit D:\My` Folders\path\to\your\app\launcher.ps1
# Start in:
"D:\My Folders\path\to\your\app"
```

- google drive auth https://developers.google.com/drive/api/quickstart/python