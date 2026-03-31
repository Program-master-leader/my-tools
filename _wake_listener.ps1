
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$info = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() | Where-Object { $_.Culture.Name -eq 'zh-CN' } | Select-Object -First 1
if ($info -ne $null) {
    $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($info)
} else {
    $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
}
$engine.SetInputToDefaultAudioDevice()
$words = @("小K","小k","小可","小客","小卡","小凯","小开","小克","晓K","晓k","肖K","肖k","小科","小壳","小K小K","小k小k","小K小k","小k小K")
$choices = New-Object System.Speech.Recognition.Choices($words)
$gb = New-Object System.Speech.Recognition.GrammarBuilder($choices)
$grammar = New-Object System.Speech.Recognition.Grammar($gb)
$engine.LoadGrammar($grammar)
$timeout = [System.TimeSpan]::FromSeconds(5)
while ($true) {
    $result = $engine.Recognize($timeout)
    if ($result -ne $null -and $result.Text -ne "" -and $result.Confidence -gt 0.1) {
        [Console]::WriteLine($result.Text)
        [Console]::Out.Flush()
    }
}
