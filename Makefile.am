AUTOMAKE_OPTIONS = foreign 1.7

#SUBDIRS = src po docs
SUBDIRS = src po

EXTRA_DIST = \
	system-config-lvm.desktop		\
	system-config-lvm.console		\
	system-config-lvm.desktop.in	\
	system-config-lvm.pam			\
	src/pixmaps/grad3.xpm			\
	src/pixmaps/UV.xpm				\
	src/pixmaps/LV.xpm				\
	src/pixmaps/PV.xpm				\
	src/pixmaps/VG.xpm				\
	src/pixmaps/lv_icon.png			\
	intltool-extract.in				\
	intltool-merge.in				\
	intltool-update.in				\
	README							\
	ChangeLog

CLEANFILES=$(applications_DATA)
DISTCLEANFILES=intltool-extract intltool-merge intltool-update
MAINTAINERCLEANFILES=ChangeLog

@INTLTOOL_DESKTOP_RULE@

.PHONY: changelog srpm

applicationsdir=$(datadir)/applications
applications_DATA=system-config-lvm.desktop
applications_in_files=$(applications_DATA:.desktop=.desktop.in)

install-data-hook:
	$(mkinstalldirs) $(DESTDIR)$(sysconfdir)/security/console.apps
	$(mkinstalldirs) $(DESTDIR)$(sysconfdir)/pam.d
	$(mkinstalldirs) $(DESTDIR)$(prefix)/bin/
	$(INSTALL_DATA) $(srcdir)/system-config-lvm.console $(DESTDIR)$(sysconfdir)/security/console.apps/system-config-lvm
	$(INSTALL_DATA) $(srcdir)/system-config-lvm.pam $(DESTDIR)$(sysconfdir)/pam.d/system-config-lvm
#	$(INSTALL_DATA) $(srcdir)/src/pixmaps/UV.xpm $(DESTDIR)$(pkgdatadir)
#	$(INSTALL_DATA) $(srcdir)/src/pixmaps/LV.xpm $(DESTDIR)$(pkgdatadir)
#	$(INSTALL_DATA) $(srcdir)/src/pixmaps/PV.xpm $(DESTDIR)$(pkgdatadir)
#	$(INSTALL_DATA) $(srcdir)/src/pixmaps/VG.xpm $(DESTDIR)$(pkgdatadir)
#	$(INSTALL_DATA) $(srcdir)/src/pixmaps/grad3.xpm $(DESTDIR)$(pkgdatadir)
	ln -fs consolehelper $(DESTDIR)$(prefix)/bin/system-config-lvm

uninstall-local:
	rm -f $(DESTDIR)$(sysconfdir)/pam.d/system-config-lvm
	rm -f $(DESTDIR)$(prefix)/bin/system-config-lvm
#	rm -f $(DESTDIR)$(pkgdatadir)/LV.xpm
#	rm -f $(DESTDIR)$(pkgdatadir)/UV.xpm
#	rm -f $(DESTDIR)$(pkgdatadir)/VG.xpm
#	rm -f $(DESTDIR)$(pkgdatadir)/PV.xpm
#	rm -f $(DESTDIR)$(pkgdatadir)/grad3.xpm

clean:
	rm -f system-config-lvm.desktop
	rm -f *~


