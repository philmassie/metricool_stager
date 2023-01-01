# Fix source file path
# [environment]::Commandline

# $srcpathfull = ''
# foreach ($arg in $args) {
# 	$srcpathfull += $arg + ' '
# }
# $srcpathfull= $srcpathfull.Trim()

conda activate py37
python.exe "D:\My Folders\vscode_projects\2022\metricool_csv\metricool_scheduler.py" $args