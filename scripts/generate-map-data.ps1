# Define the command and arguments
$exePath = ".\Source2Viewer-CLI.exe"
$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\pak01_dir.vpk"
$outputPath = "."
$folderFilter = "resource/overviews/"
$extensionFilter = "txt"
$mapDataFile = "awpy\data\map_data.py"

# Run the command
& $exePath -i $inputPath -f $folderFilter -e $extensionFilter -o $outputPath -d
$tempOutputDir = Join-Path -Path $outputPath -ChildPath $folderFilter
uv run awpy parse-overviews $tempOutputDir
uv run ruff check --fix $mapDataFile
uv run ruff format $mapDataFile
$parentPath = Split-Path -Path $tempOutputDir -Parent
Remove-Item -Path $parentPath -Recurse -Force
