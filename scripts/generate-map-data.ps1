param(
    [Parameter(Mandatory=$false)]
    [string]$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\pak01_dir.vpk",

    [Parameter(Mandatory=$false)]
    [string]$outputPath = "."
)

# Define the fixed command and filters
$exePath = ".\Source2Viewer-CLI.exe"
$folderFilter = "resource/overviews/"
$extensionFilter = "txt"

# Run the command
& $exePath -i $inputPath -f $folderFilter -e $extensionFilter -o $outputPath -d