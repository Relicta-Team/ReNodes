import subprocess
import sys
import re

pathRevisionFile = "ReNode/app/REVISION.py"
pathVersionFile = "ReNode/app/VERSION.py"
deployProjectPath = "C:/Users/Илья/Documents/Arma 3 - Other Profiles/User/missions/resdk_fork.vr/ReNode" #TODO
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
			deploySource = True
			updateVersionFileTask = True

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

if deploySource:
	import os
	import sys
	import shutil
	try:
		data = """
		pyinstaller --noconfirm --onefile --windowed --icon "./data/icon.ico" --name "ReNode" --hidden-import "NodeGraphQt" --additional-hooks-dir "./NodeGraphQt-0.6.11" --paths "."  "./main.py"
		"""

		return_ = os.system(data)
		print("Compiler result " + str(return_))
		if return_ != 0:
			raise Exception("Compiler error: Code " + str(return_))
		
		#cleanup deploy folder
		if os.path.exists(deployProjectPath):
			shutil.rmtree(deployProjectPath + "/data")
		if os.path.exists(deployProjectPath + "/ReNode.exe"):
			os.remove(deployProjectPath + "/ReNode.exe")

		print("Copy files...")
		dest = deployProjectPath

		shutil.copytree('./data',dest+"/data")
		shutil.copyfile('./dist/ReNode.exe',dest+"/ReNode.exe")

		print('Done')
		sys.exit(0)
	except Exception as e:
		print(e)
		sys.exit(1)
