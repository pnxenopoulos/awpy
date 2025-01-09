# Define the command and arguments
$exePath = ".\Source2Viewer-CLI.exe"
$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\pak01_dir.vpk"
$outputPath = "."
$folderFilter = "resource/overviews/"
$extensionFilter = "txt"

# Run the command
& $exePath -i $inputPath -f $folderFilter -e $extensionFilter -o $outputPath -d
