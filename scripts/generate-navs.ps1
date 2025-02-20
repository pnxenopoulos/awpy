param(
    [Parameter(Mandatory=$false)]
    [string]$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\maps",

    [Parameter(Mandatory=$false)]
    [string]$outputDirectory = (Get-Location).Path
)

# Define the fixed command and filters
$targetDir = "awpy\data\spawns"

# Ensure the path exists
if (Test-Path $inputPath) {
    # Get all .vpk files in the directory
    Get-ChildItem -Path $inputPath -Filter "*.vpk" | ForEach-Object {
        # Get full path and base name of the file
        $filePath = $_.FullName
        $fileNameWithoutExtension = $_.BaseName

        # Temporary output directory for the tool
        $tempOutputDir = Join-Path -Path $outputDirectory -ChildPath $fileNameWithoutExtension

        # Create a temporary directory for the output
        if (-Not (Test-Path $tempOutputDir)) {
            New-Item -ItemType Directory -Path $tempOutputDir | Out-Null
        }

        # Construct and run the Source2Viewer-CLI command
        Write-Host "Processing file: $filePath" -ForegroundColor Green
        .\Source2Viewer-CLI.exe -i $filePath -e "nav" -o $tempOutputDir -d

        # Move the output file to the current directory and rename it
        $generatedFile = Join-Path -Path $tempOutputDir -ChildPath "maps\$fileNameWithoutExtension.nav"
        $newFileName = Join-Path -Path $outputDirectory -ChildPath "$fileNameWithoutExtension.nav"

        if (Test-Path $generatedFile) {
            Move-Item -Path $generatedFile -Destination $newFileName -Force
            Write-Host "Output saved as: $newFileName" -ForegroundColor Cyan

            # Run the awpy nav command
            Write-Host "Running awpy nav on: $newFileName" -ForegroundColor Yellow
            uv run awpy nav $newFileName
            $generatedFileName = Join-Path -Path $outputDirectory -ChildPath "$fileNameWithoutExtension.json"
            Move-Item -Path $generatedFileName -Destination $targetDir -Force
            Remove-Item -Path $newFileName -Force
        } else {
            Write-Host "Error: Expected output file not found for $fileNameWithoutExtension" -ForegroundColor Red
        }

        # Clean up the temporary directory
        Remove-Item -Path $tempOutputDir -Recurse -Force
    }
} else {
    Write-Host "The specified directory does not exist: $inputPath" -ForegroundColor Red
}
