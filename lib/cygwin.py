import os
#
import cross
import download
import gub
import misc
import mingw
import gup

# FIXME: setting binutil's tooldir and/or gcc's gcc_tooldir may fix
# -luser32 (ie -L .../w32api/) problem without having to set LDFLAGS.
class Binutils (cross.Binutils):
    def makeflags (self):
        return misc.join_lines ('''
tooldir="%(cross_prefix)s/%(target_architecture)s"
''')
    def compile_command (self):
        return (cross.Binutils.compile_command (self)
                + self.makeflags ())
    def configure_command (self):
        return ( cross.Binutils.configure_command (self)
                 + ' --disable-werror ')

class W32api_in_usr_lib (gub.BinarySpec, gub.SdkBuildSpec):
    def get_build_dependencies (self):
        return ['w32api']
    def do_download (self):
        pass
    def untar (self):
        self.system ('mkdir -p %(srcdir)s/root/usr/lib')
        self.system ('''
tar -C %(system_root)s/usr/lib/w32api -cf- . | tar -C %(srcdir)s/root/usr/lib -xf-
''')

class Gcc (mingw.Gcc):
    def get_build_dependencies (self):
        return (mingw.Gcc.get_build_dependencies (self)
                + ['cygwin', 'w32api-in-usr-lib'])
    def makeflags (self):
        return misc.join_lines ('''
tooldir="%(cross_prefix)s/%(target_architecture)s"
gcc_tooldir="%(cross_prefix)s/%(target_architecture)s"
''')
    def compile_command (self):
        return (mingw.Gcc.compile_command (self)
                + self.makeflags ())

    def configure_command (self):
        return (mingw.Gcc.configure_command (self)
                + misc.join_lines ('''
--with-newlib
--enable-threads
'''))

class Gcc_core (Gcc):
    def untar (self):
        gxx_file_name = re.sub ('-core', '-g++',
                                self.expand (self.file_name ()))
        self.untar_cygwin_src_package_variant2 (gxx_file_name, split=True)
        self.untar_cygwin_src_package_variant2 (self.file_name ())

    def untar_cygwin_src_package_variant2 (self, file_name, split=False):
        '''Unpack this unbelievably broken version of Cygwin source packages.

foo-split-x.y.z-b.tar.bz2 contains foo-split-x.y.z.tar.bz2 and
foo-x.y.z-b.patch.  foo-x.y.z.tar.bz2 contains foo-x.y.z.  The patch
contains patches against all foo split source balls, so applying it
may fail partly and complain about missing files.'''
        
        flags = '-jxf'
        file_name = self.expand (file_name)
        no_src = re.sub ('-src', '', file_name)
        base = re.sub ('\.tar\..*', '', no_src)
        second_tarball = re.sub ('-[0-9]+\.tar', '.tar', no_src)
        print 'second_tarball: ' + second_tarball
        ball_re = '^([a-z]+)(-[a-z+]+)?(.*)(-[0-9]+)'
        if split:
            second_tarball_contents = re.sub (ball_re, '\\1\\2\\3', base)
        else:
            second_tarball_contents = re.sub (ball_re, '\\1\\3', base)
        print 'second_tarball_contents: ' + second_tarball_contents
        self.system ('''
rm -rf %(allsrcdir)s/%(base)s
tar -C %(allsrcdir)s %(flags)s %(downloaddir)s/%(file_name)s
tar -C %(allsrcdir)s %(flags)s %(allsrcdir)s/%(second_tarball)s
''',
                     locals ())
        if split:
            return
        patch = re.sub (ball_re, '\\1\\3\\4.patch', base)
        print 'patch: ' + patch
        self.system ('''
cd %(allsrcdir)s && mv %(second_tarball_contents)s %(base)s
cd %(srcdir)s && patch -p1 -f < %(allsrcdir)s/%(patch)s || true
''',
                     locals ())

# download-only package
class Gcc_gxx (gub.NullBuildSpec):
    pass

mirror = 'http://ftp.uni-kl.de/pub/windows/cygwin'
def get_cross_packages (settings):
    import linux
    # FIXME: must add deps to buildeps, otherwise packages do not
    # get built in correct dependency order?
    cross_packs = [
        Binutils (settings).with (version='20050610-1', format='bz2', mirror=download.cygwin),
        W32api_in_usr_lib (settings).with (version='1.0'),
        Gcc (settings).with (version='4.1.1', mirror=download.gcc_41, format='bz2'),
#        linux.Guile_config (settings).with (version='1.6.7'),
        linux.Python_config (settings).with (version='2.4.3'),
        ]

    return cross_packs

def change_target_packages (packages):
    cross.change_target_packages (packages)

    # FIXME: this does not work (?)
    for p in packages.values ():
        old_callback = p.get_build_dependencies
        p.get_build_dependencies = cross.MethodOverrider (old_callback,
                                                          lambda old_val, extra_arg: old_val + extra_arg, (['cygwin'],)).method
        
        # FIXME: why do cross packages get here too?
        if isinstance (p, cross.CrossToolSpec):
            continue
        gub.change_target_dict (p, {
            'DLLTOOL': '%(tool_prefix)sdlltool',
            'DLLWRAP': '%(tool_prefix)sdllwrap',
            'LDFLAGS': '-L%(system_root)s/usr/lib -L%(system_root)s/usr/bin -L%(system_root)s/usr/lib/w32api',
            })
        

import gup
from new import classobj
from new import instancemethod
import gub
import re

def get_cygwin_package (settings, name, dict):
    package_class = classobj (name, (gub.BinarySpec,), {})
    package = package_class (settings)
    package.name_dependencies = []
    if dict.has_key ('requires'):
        deps = re.sub ('\([^\)]*\)', '', dict['requires']).split ()
        deps = [x.strip ().lower ().replace ('_', '-') for x in deps]
        ##print 'gcp: ' + `deps`
        cross = [
            'base-passwd', 'bintutils',
            'gcc', 'gcc-core', 'gcc-g++',
            'gcc-mingw', 'gcc-mingw-core', 'gcc-mingw-g++',
            ]
        cycle = ['base-passwd']
        source = [
            'guile-devel',
            'libtool1.5', 'libltdl3',
            'libguile12', 'libguile16',
            ]
        #urg_source_deps_are_broken = ['guile', 'libtool']
        #source += urg_source_deps_are_broken
        # FIXME: These packages are not needed for [cross] building,
        # but most should stay as distro's final install dependency.
        unneeded = [
            'bash',
            'coreutils',
            'ghostscript-base', 'ghostscript-x11',
            '-update-info-dir',
            'libxft', 'libxft1', 'libxft2',
            'libbz2-1',
            'tcltk',
            'x-startup-scripts',
            'xaw3d',
            'xorg-x11-bin-lndir',
            'xorg-x11-etc',
            'xorg-x11-fnts',
            'xorg-x11-libs-data',
            ]
        blacklist = cross + cycle + source + unneeded
        deps = filter (lambda x: x not in blacklist, deps)
        package.name_dependencies = deps

    def get_build_dependencies (self):
        return self.name_dependencies
    package.get_build_dependencies = instancemethod (get_build_dependencies,
                                                     package, package_class)
    package.ball_version = dict['version']
        
    package.url = (mirror + '/'
           + dict['install'].split ()[0])
    package.format = 'bz2'
    return package

## UGH.   should split into parsing  package_file and generating gub specs.
def get_cygwin_packages (settings, package_file):
    dist = 'curr'

    dists = {'test': [], 'curr': [], 'prev' : []}
    chunks = open (package_file).read ().split ('\n\n@ ')
    for i in chunks[1:]:
        lines = i.split ('\n')
        name = lines[0].strip ()
        name = name.lower ()
        
        blacklist = ('binutils', 'gcc',
                     ### FIXME: guile should be read from
                     ### generated gub-setup.ini
                     ###'guile', 'guile-devel', 'libguile12', 'libguile16',
                     ### FIXME: we need our own libtool 
                     'libtool', 'libtool1.5', 'libtool-devel', 'libltdl3',
                     ### FIXME: we need to build lilypond from source
                     'lilypond')
        
        if name in blacklist:
            continue
        packages = dists['curr']
        records = {
            'sdesc': name,
            'version': '0-0',
            'install': 'urg 0 0',
            }
        j = 1
        while j < len (lines) and lines[j].strip ():
            if lines[j][0] == '#':
                j = j + 1
                continue
            elif lines[j][0] == '[':
                packages.append (get_cygwin_package (settings, name, records.copy ()))
                packages = dists[lines[j][1:5]]
                j = j + 1
                continue

            try:
                key, value = [x.strip () for x in lines[j].split (': ', 1)]
            except KeyError: ### UGH -> what kind of exceptino?
                print lines[j], package_file
                raise 'URG'
            if (value.startswith ('"')
              and value.find ('"', 1) == -1):
                while 1:
                    j = j + 1
                    value += '\n' + lines[j]
                    if lines[j].find ('"') != -1:
                        break
            records[key] = value
            j = j + 1
        packages.append (get_cygwin_package (settings, name, records))

    # debug
    names = [p.name() for p in dists[dist]]
    names.sort()

    return dists[dist]



class Cygwin_dependency_finder:
    def __init__ (self, settings):
        self.settings = settings
        self.packages = {}
        
    def download (self):
        url = mirror + '/setup.ini'
        # FIXME: download/offline
        downloaddir = self.settings.downloaddir
        file = self.settings.downloaddir + '/setup.ini'
        if not os.path.exists (file):
            misc.download_url (url, self.settings.downloaddir)

        pack_list  = get_cygwin_packages (self.settings, file)
        for p in pack_list:
            self.packages[p.name ()] = p

    def get_dependencies (self, name):
        return self.packages[name]
        
cygwin_dep_finder = None

def init_cygwin_package_finder (settings):
    global cygwin_dep_finder
    cygwin_dep_finder  = Cygwin_dependency_finder (settings)
    cygwin_dep_finder.download ()

def cygwin_name_to_dependency_names (name):
    return cygwin_dep_finder.get_dependencies (name)
