import sublime, sublime_plugin, os, shutil, re, string, textwrap, urllib
from bs4 import BeautifulSoup
from Carbon.CoreFoundation import *
from Carbon.CF import *

class DwSiteImporterCommand(sublime_plugin.WindowCommand):
	def run(self):		
		if sublime.platform() == "windows":
			self.default_project_path = os.path.expanduser("~\\Desktop\\")
		else:
			self.default_project_path = os.path.expanduser("~/Desktop/")
		self.window.show_input_panel("Folder containing .ste files:", self.default_project_path, self.on_folder_select, None, None)

	def word_wrap(self, text, width=80, separator='\n'):

		if width >= len(text):
			return text

		buff = []
		while True:
			found_space = False
			for i in range(width, 0, -1):
				if text[i].isspace():
					buff.append(text[:i])
					text = text[i:].strip()
					found_space = True
					break
				if not found_space:
					buff.append(text[:width])
					text = text[width:].strip()
				if len(text) <= width:
					buff.append(text)
					return separator.join(buff)


	def on_folder_select(self, folder):		
		if sublime.platform() == "windows":
			if folder.endswith("\\") == False:
				folder = folder + "\\"
		else:
			if folder.endswith("/") == False:
				folder = folder + "/"
		
		if not os.path.isdir(folder):
			return
		
		self.folder = folder
		self.folderfiles = []
		self.currentfilenum = -1
		
		self.projectfilesfolder = ''
		
		for filename in os.listdir(folder):
			if not ".ste" in filename: continue
			self.folderfiles.append(filename)
		
		self.folderfilescount = len(self.folderfiles)
		self.get_project_file_location()

	def get_project_file_location(self):
		self.window.show_quick_panel([['With Site files', 'Store the .sublime-project file in the site files directory'], ['In Custom directory', 'Store the .sublime-project files in a custom directory']], self.on_project_file_location)

	def on_project_file_location(self, index):
		if index == 0:
			self.process_file()
		else:
			self.window.show_input_panel("Directory to save the .sublime-project files into:", self.default_project_path, self.on_project_file_folder_select, None, None)
		
	def on_project_file_folder_select(self, folder):
		if sublime.platform() == "windows":
			if folder.endswith("\\") == False:
				folder = folder + "\\"
		else:
			if folder.endswith("/") == False:
				folder = folder + "/"
		
		if os.path.isdir(folder):
			self.projectfilesfolder = folder
			self.process_file()
		
	def process_file(self):
		self.currentfilenum += 1
				
		if ((self.currentfilenum + 1) > self.folderfilescount):
			sublime.status_message('Finished Importing sites')
			print 'Finished Importing sites'
			return
			
		self.currentfilename = self.folderfiles[self.currentfilenum]
		self.currentste = BeautifulSoup(open(self.folder + self.currentfilename))
		
		sitename = self.currentste.site.localinfo['sitename']
		sitename = urllib.unquote(sitename.encode('ascii')).decode('utf-8')
				
		localroot = self.currentste.site.localinfo['localroot']
		u = toCF(localroot).CFURLCreateWithFileSystemPath(kCFURLHFSPathStyle, False)
		localroot = u.CFURLCopyFileSystemPath(kCFURLPOSIXPathStyle).toPython()
		localroot = urllib.unquote(localroot.encode('ascii')).decode('utf-8')
		self.localroot = localroot
		
		if not os.path.isdir(self.localroot):
			if sublime.platform() != "windows":
				# Try manually adding the Volumes dir, just incase
				localroottmp = "/Volumes"+self.localroot
				if not os.path.isdir(localroottmp):
					sublime.error_message(sitename+" localroot (" + self.localroot + ") doesn't exist.")
					print sitename+" localroot (" + self.localroot + ") doesn't exist."
					self.process_file()
					return
				else:
					self.localroot = localroottmp
			else:
				sublime.error_message(sitename+" localroot (" + self.localroot + ") doesn't exist.")
				print sitename+" localroot (" + self.localroot + ") doesn't exist."
				self.process_file()
		
		sublime.status_message('Importing site "' + sitename + '"')
		print 'Importing site "' + sitename + '"'
		
		file_name = self.currentste.site.localinfo['sitename'] + ".sublime-project"
		if self.projectfilesfolder != '':
			project_file = os.path.join(self.projectfilesfolder, file_name)
		else:
			project_file = os.path.join(self.localroot, file_name)
		file_ref = open(project_file, "w")
		file_ref.write(("{\n"
						"    \"folders\":\n"
						"    [\n"
						"        {\n"
						"            \"path\": \""+ self.localroot +"\"\n"
						"        }\n"
						"    ]\n"
						"}\n"));
		file_ref.close()
		
		servers = self.currentste.site.serverlist.find_all("server")
		self.currentsiteservers = []
		self.currentsiteserverslist = []
		self.currentsiteserverslist.append(['', 'Choose the '+sitename + ' main server'])
		
		if len(servers) > 0:
			for serveri in range(len(servers)):
				server = servers[serveri]
				if server['accesstype'] != "ftp": continue
				self.currentsiteservers.append(server)
				self.currentsiteserverslist.append(server['name'])
			
			self.confirm_main_server()
			
		else:
			self.process_file()	
			
	def confirm_main_server(self):
		self.currentsiteserverscount = len(self.currentsiteservers)			
		if self.currentsiteserverscount > 1:
			
			for serveri in range(len(self.currentsiteservers)):
				server = self.currentsiteservers[serveri]
				if server.has_key("servertype"):
					if server['servertype'] == "remoteServer":
						self.on_choose_main_server(serveri + 1)
						return
			
			self.window.show_quick_panel(self.currentsiteserverslist, self.on_choose_main_server)
		elif self.currentsiteserverscount == 1:
			self.on_choose_main_server(1)
		else:
			self.process_file()
			
			
	def on_choose_main_server(self, index):
		if index == -1:	
			self.confirm_main_server()
			return
		elif index == 0:
			self.process_file()
			return
			
		index -= 1
			
		serverstext = ""
		for serveri in range(len(self.currentsiteservers)):
			server = self.currentsiteservers[serveri]
			
			encodedpassword = server['pw']
			passwordarr = (self.word_wrap(encodedpassword, 2, ' ')+'').split(' ')
			password = ''
			for i in range(len(passwordarr)):
				password = password + chr(int(passwordarr[i], 16)-i)

			if not ":" in server['host']:
				port = 21
				type = 'ftp'
				if server['usesftp'] == "TRUE":
					port = 22
					type = 'sftp'
			else:
				hostport = server['host'].split(':')
				server['host'] = hostport[0]
				port = hostport[1]
				type = 'ftp'
				if server['usesftp'] == "TRUE":
					type = 'sftp'

			comment = '//'
			if index == serveri:
				comment = ''
				
			passivemode = 'true'
			if server['useftpoptimization'] == "FALSE":
				passivemode = 'false'
				
			if not server['remoteroot'].startswith('/'):
				server['remoteroot'] = '/' + server['remoteroot']
			
			serverstext = serverstext + ("\n    // " + server['name'] + "\n"
		    							 "    "+comment+"\"type\": \"" + type + "\",\n"
		    							 "    "+comment+"\"host\": \"" + server['host'] + "\",\n"
										 "    "+comment+"\"user\": \"" + server['user'] + "\",\n"
		    							 "    "+comment+"\"password\": \"" + password + "\",\n"
		    							 "    "+comment+"\"port\": \"" + str(port) + "\",\n"
		    							 "    "+comment+"\"remote_path\": \"" + server['remoteroot'] + "\",\n"
		    							 "    "+comment+"\"ftp_passive_mode\": " + passivemode + ",\n");
		
		
		file_name = "sftp-config.json"
		ftpconfig_file = os.path.join(self.localroot, file_name)
		file_ref = open(ftpconfig_file, "w")
		file_ref.write(("{\n"
						+ serverstext + 
						"\n"
						"    \"connect_timeout\": 30,\n"
						"\n"
						"    \"save_before_upload\": true,\n"
						"    \"upload_on_save\": false,\n"
						"    \"sync_down_on_open\": false,\n"
						"    \"sync_skip_deletes\": false,\n"
						"    \"confirm_downloads\": false,\n"
						"    \"confirm_sync\": true,\n"
						"    \"confirm_overwrite_newer\": false,\n"
						"\n"
						"    \"ignore_regex\": \"(\\\.sublime-project|\\\.sublime-workspace|sftp-config(-alt\\\d?)?\\\.json|sftp-settings\\\.json|/venv/|\\\.svn|\\\.hg|\\\.git|\\\.bzr|_darcs|CVS|\\\.DS_Store|Thumbs\\\.db|desktop\\\.ini)\",\n"
						"    //\"file_permissions\": \"664\",\n"
						"    //\"dir_permissions\": \"775\",\n"
						"    //\"ssh_key_file\": \"~/.ssh/id_rsa\",\n"
						"    //\"sftp_flags\": \"-F /path/to/ssh_config\",\n"
						"\n"
						"    \"preserve_modification_times\": false,\n"
						"    \"remote_time_offset_in_hours\": 0,\n"
						"    \"remote_encoding\": \"utf-8\",\n"
						"    \"remote_locale\": \"C\",\n"
						"\n"
						"}\n"));
		file_ref.close()		
		
		self.process_file()