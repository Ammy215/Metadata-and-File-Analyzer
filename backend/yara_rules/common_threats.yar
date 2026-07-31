rule Suspicious_Strings {
    meta:
        description = "Detects suspicious command strings"
        severity = "HIGH"
    strings:
        $s1 = "cmd.exe" nocase
        $s2 = "powershell" nocase
        $s3 = "reg add" nocase
        $s4 = "wmic" nocase
    condition:
        any of them
}

rule Possible_Malware {
    meta:
        description = "Detects potential malware patterns"
        severity = "CRITICAL"
    strings:
        $m1 = "WinExec" nocase
        $m2 = "CreateRemoteThread" nocase
        $m3 = "SetWindowsHookEx" nocase
    condition:
        any of them
}

rule Obfuscation_Indicators {
    meta:
        description = "Detects code obfuscation techniques"
        severity = "HIGH"
    strings:
        $o1 = "eval(" nocase
        $o2 = "base64" nocase
        $o3 = "URLDecode" nocase
    condition:
        any of them
}
