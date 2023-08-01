import subprocess
import sys
import re

pathRevisionFile = "ReNode/app/REVISION.py"
pathVersionFile = "ReNode/app/VERSION.py"
deployProjectPath = "path_to_resdk_deploy" #TODO

print(f"Start builder. Args: {sys.argv}")

# arguments inputed: major, minor
#get arguments
doUpdateMajor = False
doUpdateMinor = False
updateVersionFileTask = False
deploySource = False
args = sys.argv
if len(args) > 1:
	#iterate
	for argval in args[1:]:
		if argval == "major":
			doUpdateMajor = True
			updateVersionFileTask = True
		elif argval == "minor":
			doUpdateMinor = True
			updateVersionFileTask = True
		elif argval == "deploy":
			print("Deploy not implemented now")

if updateVersionFileTask:
	print("Update version file")
	# read version file
	versioncontent = open(pathVersionFile).read()

	# regex get version values from array
	version = re.findall(r'\d+', versioncontent)
	#parse version str to int
	version = [int(x) for x in version]
	if doUpdateMajor:
		version[0] += 1
	if doUpdateMinor:
		version[1] += 1

	# write to version file
	open(pathVersionFile, 'w').write("global_version = " + str(version))


# write git short to revision file
print("Update revision file")
# get git rev-parse
revision = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('utf-8')
revision = str(revision).replace('\\n', '').replace('\r','').replace('\n','')
open(pathRevisionFile, 'w').write("global_revision = \"" + str(revision) + "\"")