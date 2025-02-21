# Note: On Windows you must keep the .dll from the .zip in the same directory as the .exe
param(
    [Parameter(Mandatory=$false)]
    [string]$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\pak01_dir.vpk",

    [Parameter(Mandatory=$false)]
    [string]$outputPath = "."
)

# Define the fixed command and filters
$exePath = ".\Source2Viewer-CLI.exe"
$folderFilter = "panorama/images/overheadmaps/"
$extensionFilter = "vtex_c"
$targetDir = "awpy\data\maps\"

# Run the command
& $exePath -i $inputPath -f $folderFilter -e $extensionFilter -o $outputPath -d

# Set the directory for renaming files
$targetDirectory = Join-Path $outputPath $folderFilter

# Check if the target directory exists
if (Test-Path $targetDirectory) {
    # Get all files ending with "_radar_psd.png"
    Get-ChildItem -Path $targetDirectory -Filter "*_radar_psd.png" | ForEach-Object {
        # Skip files that contain "skipString1" or "skipString2" in their name
        if ($_.Name -like "*_preview*" -or $_.Name -like "*_vanity*") {
            continue
        }

        # Define the new file name by replacing "_radar_psd.png" with ".png"
        $newFileName = $_.Name -replace "_radar_psd\.png$", ".png"
        $newFilePath = Join-Path $_.DirectoryName $newFileName

        # Rename the file
        Rename-Item -Path $_.FullName -NewName $newFileName
        $currentPath = Join-Path $folderFilter $newFileName
        $targetPath = Join-Path $targetDir $newFileName
        Write-Host $currentPath
        Write-Host $targetPath
        Move-Item -Path $currentPath -Destination $targetPath -Force
    }
    Remove-Item -Path "panorama" -Recurse -Force
} else {
    Write-Host "Target directory '$targetDirectory' does not exist."
}
