Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
$engine.SetInputToDefaultAudioDevice()
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)
$timeout = [System.TimeSpan]::FromSeconds(10)
$result = $engine.Recognize($timeout)
if ($result -ne $null) {
    Write-Output $result.Text
} else {
    Write-Output ""
}
