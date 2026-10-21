Option Explicit
' Masaustune ve Baslat menusune GOLGE kisayolu koyar (bir kez calistirmak yeterli).
Dim sh, fso, root, Q, title, icon, made, lnk, answer
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Q = Chr(34)
title = "G" & ChrW(214) & "LGE"
root = fso.GetParentFolderName(WScript.ScriptFullName)
icon = root & "\config\ultron.ico"

If Not fso.FileExists(root & "\GOLGE.vbs") Then
  MsgBox "GOLGE.vbs bulunamadi. Bu dosyayi GOLGE klasorunun icinden calistir.", vbCritical, title
  WScript.Quit 1
End If

Sub MakeShortcut(folder)
  Dim s
  Set s = sh.CreateShortcut(folder & "\" & title & ".lnk")
  s.TargetPath = "wscript.exe"
  s.Arguments = "//nologo " & Q & root & "\GOLGE.vbs" & Q
  s.WorkingDirectory = root
  s.Description = title & " masaustu asistani"
  If fso.FileExists(icon) Then s.IconLocation = icon
  s.Save
End Sub

MakeShortcut sh.SpecialFolders("Desktop")
MakeShortcut sh.SpecialFolders("Programs")
made = "Masaustu ve Baslat menusu"

answer = MsgBox("Bilgisayar acilinca " & title & " kendiliginden baslasin mi?", vbYesNo + vbQuestion, title)
If answer = vbYes Then
  MakeShortcut sh.SpecialFolders("Startup")
  made = made & " ve Baslangic"
End If
MsgBox made & " kisayolu olusturuldu. Artik " & title & " simgesine cift tiklaman yeterli.", vbInformation, title
