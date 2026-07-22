; NSIS Installer for Windows
Name "Nexus Remote"
OutFile "NexusRemote-Setup.exe"
InstallDir "\Nexus Remote"
RequestExecutionLevel admin

Section "Install"
    SetOutPath 
    File /r "dist\*.*"
    CreateShortCut "\Nexus Remote.lnk" "\nexus_client.exe"
SectionEnd
