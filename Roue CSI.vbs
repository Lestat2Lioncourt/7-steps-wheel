' Roue CSI - Lanceur silencieux
' Lance start.py sans fenetre console. Le navigateur s'ouvre automatiquement.

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Repertoire de ce script (= racine de l'app)
appDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Chercher Python
pythonExe = ""

' 1. python dans le PATH
On Error Resume Next
WshShell.Run "cmd /c python --version", 0, True
If Err.Number = 0 Then
    pythonExe = "python"
End If
On Error GoTo 0

' 2. pythonw (lance sans console)
If pythonExe = "" Then
    On Error Resume Next
    WshShell.Run "cmd /c pythonw --version", 0, True
    If Err.Number = 0 Then
        pythonExe = "pythonw"
    End If
    On Error GoTo 0
End If

If pythonExe = "" Then
    MsgBox "Python n'a pas ete trouve sur ce poste." & vbCrLf & vbCrLf & _
           "Contactez votre administrateur pour l'installation.", _
           vbExclamation, "Roue CSI"
    WScript.Quit
End If

' Lancer start.py avec pythonw (pas de console) depuis le repertoire de l'app
WshShell.CurrentDirectory = appDir
WshShell.Run "pythonw """ & appDir & "\start.py""", 0, False
