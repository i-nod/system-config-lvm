PYTHON_FILES = \
	InputController.py \
	CommandHandler.py  \
	CommandError.py  \
	lvm_model.py \
	lvmui_constants.py \
	Properties_Renderer.py \
	renderer.py \
	Volume_Tab_View.py \
	fdisk_wrapper.py \
	parted_wrapper.py \
	Partition.py	\
	BlockDevice.py	\
	BlockDeviceModel.py	\
	Filesystem.py	\
	Fstab.py	\
	execute.py	\
	migrate_extents.glade	\
	lv_edit_props.glade	\
	cylinder_items.py	\
	PhysicalVolume.py	\
	LogicalVolume.py	\
	VolumeGroup.py	\
	Volume.py	\
	Segment.py		\
	ExtentBlock.py	\
	WaitMsg.py	\
	Multipath.py	\
	utilities.py	\
	Cluster.py      \
	pixmaps/UV.xpm	\
	pixmaps/VG.xpm	\
	pixmaps/LV.xpm	\
	pixmaps/PV.xpm	\
	pixmaps/grad3.xpm	\
	pixmaps/lv_icon.png	\
	system-config-lvm.py

GLADE_FILES = lvui.glade migrate_extents.glade lv_edit_props.glade Filesystem.glade

EXTRA_DIST = $(PYTHON_FILES) $(GLADE_FILES)

execdir = $(sbindir)

all-local: 
	rm -f system-config-lvm
	ln -s system-config-lvm.py system-config-lvm

gladedir = $(pkgdatadir)
glade_DATA = $(GLADE_FILES)

install-exec-local:
	mkdir -p $(DESTDIR)$(sbindir) $(DESTDIR)$(bindir) $(DESTDIR)$(pkgdatadir) $(DESTDIR)$(pkgdatadir)/pixmaps/
	sed -e 's/\@VERSION\@/@VERSION@/g' $(srcdir)/system-config-lvm.py > $(DESTDIR)$(pkgdatadir)/system-config-lvm.py
	chmod 755 $(DESTDIR)$(pkgdatadir)/system-config-lvm.py
	install -m 0644 $(srcdir)/InputController.py $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/CommandHandler.py $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/CommandError.py $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/lvm_model.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/lvmui_constants.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/Properties_Renderer.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/renderer.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/Volume_Tab_View.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/fdisk_wrapper.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/parted_wrapper.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/Partition.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/BlockDevice.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/BlockDeviceModel.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/Filesystem.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/Fstab.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/execute.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/migrate_extents.glade  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/lv_edit_props.glade  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/Filesystem.glade  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/cylinder_items.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/PhysicalVolume.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/LogicalVolume.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/VolumeGroup.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/Volume.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/Segment.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/ExtentBlock.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/WaitMsg.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/Multipath.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/utilities.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/Cluster.py  $(DESTDIR)$(pkgdatadir)/
	install -m 0644 $(srcdir)/pixmaps/PV.xpm  $(DESTDIR)$(pkgdatadir)/pixmaps/
	install -m 0644 $(srcdir)/pixmaps/LV.xpm  $(DESTDIR)$(pkgdatadir)/pixmaps/
	install -m 0644 $(srcdir)/pixmaps/UV.xpm  $(DESTDIR)$(pkgdatadir)/pixmaps/
	install -m 0644 $(srcdir)/pixmaps/VG.xpm  $(DESTDIR)$(pkgdatadir)/pixmaps/
	install -m 0644 $(srcdir)/pixmaps/grad3.xpm  $(DESTDIR)$(pkgdatadir)/pixmaps/
	install -m 0644 $(srcdir)/pixmaps/lv_icon.png  $(DESTDIR)$(pkgdatadir)/pixmaps/
	softdir=$(pkgdatadir); \
	p=$(DESTDIR) ; \
	softdir=$${softdir/#$$p} ; \
	p=$(prefix) ; \
	softdir=$${softdir/#$$p} ; \
	softdir=$${softdir/#\/} ; \
	ln  -fs ../$${softdir}/system-config-lvm.py $(DESTDIR)$(sbindir)/system-config-lvm;

uninstall-local:
	rm -fr $(DESTDIR)$(pkgdatadir)
	rm -f  $(DESTDIR)$(sbindir)/system-config-lvm

docs:
	cd $(srcdir)
	python @PYDOC@ -w $(PYTHON_FILES)
	mv *.html doc

pycheck:
	pychecker -F $(top_srcdir)/pycheckrc $(PYTHON_FILES)

clean:
	rm -f *.pyo *.pyc
	rm -f ${BUILT_SOURCES}
