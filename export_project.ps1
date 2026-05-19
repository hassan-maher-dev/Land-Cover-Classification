$output = "$PSScriptRoot\project_for_ai.txt"

# الملفات النصية المسموح بيها
$textExtensions = @(
    "*.py","*.js","*.ts","*.jsx","*.tsx",
    "*.html","*.css","*.scss",
    "*.dart","*.java","*.kt","*.swift",
    "*.tf","*.tfvars","*.hcl",
    "*.yaml","*.yml","*.json",
    "*.xml","*.gradle","*.properties",
    "*.md","*.txt","*.sh","*.ps1",
    "*.sql","*.env","*.conf","*.cfg"
)

# ملفات وفولدرات يتم تجاهلها
$excludePatterns = @(
    "*\.git\*",
    "*\node_modules\*",
    "*\.dart_tool\*",
    "*\build\*",
    "*\.terraform\*",
    "*\Pods\*",
    "*\.idea\*",
    "*\.vscode\*",
    "*\dist\*",
    "*\bin\*",
    "*\obj\*"
)

# امتدادات binary ممنوعة
$binaryExtensions = @(
    "*.png","*.jpg","*.jpeg","*.gif","*.webp",
    "*.mp4","*.mp3","*.wav",
    "*.zip","*.rar","*.7z",
    "*.exe","*.dll","*.so",
    "*.jar","*.apk","*.ipa",
    "*.pdf","*.docx","*.xlsx",
    "*.tflite","*.pt","*.onnx"
)

# حذف الملف القديم لو موجود
if (Test-Path $output) {
    Remove-Item $output
}

Get-ChildItem -Recurse -File | ForEach-Object {

    $file = $_
    $path = $file.FullName
    $name = $file.Name

    $isExcluded = $false

    foreach ($pattern in $excludePatterns) {
        if ($path -like $pattern) {
            $isExcluded = $true
        }
    }

    foreach ($pattern in $binaryExtensions) {
        if ($name -like $pattern) {
            $isExcluded = $true
        }
    }

    $isTextFile = $false

    foreach ($ext in $textExtensions) {
        if ($name -like $ext) {
            $isTextFile = $true
        }
    }

    if ($isTextFile -and -not $isExcluded) {

        Add-Content $output "`n=================================================="
        Add-Content $output "FILE: $path"
        Add-Content $output "=================================================="

        try {
            Get-Content $path -ErrorAction Stop | Add-Content $output
        }
        catch {
            Add-Content $output "[ERROR READING FILE]"
        }
    }
}

Write-Host "`nDone! Output saved to:"
Write-Host $output