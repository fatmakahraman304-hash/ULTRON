Option Explicit
' GOLGE masaustu baslatici: cift tikla, komut penceresi acilmaz.
' Ilk calistirmada kurulum yoksa INSTALL.bat'i (gorunur pencerede) bir kez calistirir.
Dim sh, fso, root, py, ps1, log, Q, rc, cmd, title
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Q = Chr(34)
title = "G" & ChrW(214) & "LGE"
root = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = root
py = root & "\.venv\Scripts\python.exe"
ps1 = root & "\scripts\bootstrap.ps1"
If Not fso.FolderExists(root & "\logs") Then fso.CreateFolder root & "\logs"
log = root & "\logs\golge-baslat.log"

If Not fso.FileExists(ps1) Then
  MsgBox "scripts\bootstrap.ps1 bulunamadi. Bu dosyayi GOLGE klasorunun icinden calistir.", vbCritical, title
  WScript.Quit 1
End If

If Not fso.FileExists(py) Then
  If MsgBox(title & " ilk kez kuruluyor (birkac dakika surebilir, internet gerekir). Devam edilsin mi?", vbYesNo + vbQuestion, title) <> vbYes Then WScript.Quit 0
  rc = sh.Run("cmd /c " & Q & Q & root & "\INSTALL.bat" & Q & Q, 1, True)
  If rc <> 0 Or Not fso.FileExists(py) Then
    MsgBox "Kurulum tamamlanamadi. Ayrinti icin logs klasorune bak.", vbCritical, title
    WScript.Quit 1
  End If
End If

' Ilk acilista arayuz derlenebilir; pencere gelene kadar kisa bir bilgi goster.
sh.Popup title & " baslatiliyor...", 3, title, 64
cmd = "cmd /c " & Q & "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File " & Q & ps1 & Q & " -Mode start >> " & Q & log & Q & " 2>&1" & Q
rc = sh.Run(cmd, 0, True)
If rc <> 0 Then
  If MsgBox(title & " beklenmedik sekilde kapandi (kod " & rc & "). Kayit dosyasi acilsin mi?", vbYesNo + vbExclamation, title) = vbYes Then
    sh.Run "notepad.exe " & Q & log & Q, 1, False
  End If
End If
