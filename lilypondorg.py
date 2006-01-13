#!/usr/bin/python


## Check lilypond.org to see which buildnumbers have been uploaded.

import urllib
import re
import string
import sys

platforms = ['linux-x86',
	     'darwin-ppc',
	     'freebsd-x86',
	     'mingw']

def get_versions (platform):
	index = urllib.urlopen ('http://lilypond.org/download/binaries/%(platform)s/'
				% locals ()).read()

	versions = []
	def note_version (m):
		version = tuple (map (string.atoi,  m.group (1).split('.')))
		build = string.atoi (m.group (2))
		
		versions.append ((version, build))
		return ''

	re.sub (r'lilypond-([0-9.]+)-([0-9]+)\.[a-z-]+\.[a-z-]+', note_version, index)
	return versions

def get_max_builds (platform):
	vs = get_versions (platform)

	builds = {}
	for (version, build) in vs:
		if builds.has_key (version):
			build = max (build, builds[version])

		builds[version] = build

	return builds
	
def max_version_build (platform):
	vbs = get_versions (platform)
	vs = [v for (v,b) in vbs]
	vs.sort()
	max_version = vs[-1]

	max_b = 0
	for (v,b) in get_versions (platform):
		if v == max_version:
			max_b = max (b, max_b)

	return (max_version, max_b)

def uploaded_build_number (version):
	platform_versions = {}
	build = 0
	for p in platforms:
		vs = get_max_builds (p)
		if vs.has_key (version):
			build = max (build, vs[version])

	return build



if __name__ == '__main__':
	if len (sys.argv) <= 2:
		print 'use: lilypondorg.py maxbuild X.Y.Z'
		sys.exit (1)

	if sys.argv[1] == 'nextbuild':
		version = tuple (map (string.atoi, sys.argv[2].split ('.')))
		print uploaded_build_number (version) + 1

	else:
		pass
	#print max_version_build ('darwin-ppc')
	
	
	     
